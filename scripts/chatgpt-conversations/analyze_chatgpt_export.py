#!/usr/bin/env python3
"""
Analyze ChatGPT export conversations.json and group conversations into broad themes.

Outputs (in ./out by default):
- conversations_flat.csv               (one row per conversation)
- conversations_messages_sample.csv    (optional: small sample of messages)
- clusters.csv                         (conversation_id -> cluster_id + label)
- cluster_terms.json                   (cluster_id -> top terms)
- cluster_summary.csv                  (cluster counts + top terms)
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Minimal, common offline ML stack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


# ----------------------------
# Parsing helpers
# ----------------------------

def _safe_dt(ts: Any) -> Optional[str]:
    """Convert Unix timestamp (seconds) to ISO string. Return None if invalid."""
    try:
        if ts is None:
            return None
        # Some exports store floats/ints in seconds.
        ts = float(ts)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.isoformat()
    except Exception:
        return None


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _extract_text_from_content(content: Any) -> str:
    """
    Export formats vary. This tries to pull human-readable text from common shapes.
    """
    if content is None:
        return ""

    # Most common: {"content_type":"text","parts":[...]}
    if isinstance(content, dict):
        parts = content.get("parts")
        if isinstance(parts, list):
            joined = "\n".join(p for p in parts if isinstance(p, str))
            return joined

        # Sometimes stored as "text"
        txt = content.get("text")
        if isinstance(txt, str):
            return txt

        # Sometimes: {"result":"..."} or {"output":"..."}
        for k in ("result", "output", "message", "value"):
            v = content.get(k)
            if isinstance(v, str):
                return v

        return ""

    # Sometimes just a string
    if isinstance(content, str):
        return content

    # Sometimes list of strings
    if isinstance(content, list):
        joined = "\n".join(x for x in content if isinstance(x, str))
        return joined

    return ""


def _iter_nodes(convo: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    ChatGPT export often has a 'mapping' dict of nodes.
    Each node typically has:
      - message: { author: {role}, content: {...}, create_time, ...}
    """
    mapping = convo.get("mapping")
    if isinstance(mapping, dict):
        nodes = []
        for _, node in mapping.items():
            if isinstance(node, dict):
                nodes.append(node)
        return nodes

    # Some variants may store messages directly
    msgs = convo.get("messages")
    if isinstance(msgs, list):
        # Wrap to resemble node.message shape
        nodes = []
        for m in msgs:
            if isinstance(m, dict):
                nodes.append({"message": m})
        return nodes

    return []


def flatten_conversations(
    conversations_json_path: str,
    include_system: bool = False,
    include_tool: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns:
      df_convos: one row per conversation (id/title/timestamps/doc_text/turn_counts)
      df_sample_messages: optional message-level table (for debugging / preview)
    """
    with open(conversations_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Expected conversations.json to be a JSON array (list).")

    convo_rows = []
    sample_msg_rows = []

    for convo in data:
        if not isinstance(convo, dict):
            continue

        convo_id = convo.get("id") or convo.get("conversation_id") or convo.get("uuid")
        title = convo.get("title") or ""
        create_time = _safe_dt(convo.get("create_time"))
        update_time = _safe_dt(convo.get("update_time"))

        nodes = _iter_nodes(convo)

        # Collect messages sorted by create_time if available
        messages = []
        for node in nodes:
            msg = node.get("message") if isinstance(node, dict) else None
            if not isinstance(msg, dict):
                continue

            author = msg.get("author", {})
            role = ""
            if isinstance(author, dict):
                role = author.get("role") or ""
            elif isinstance(author, str):
                role = author

            if role == "system" and not include_system:
                continue
            if role in ("tool", "function") and not include_tool:
                continue

            content = msg.get("content")
            text = _extract_text_from_content(content)
            text = _normalize_ws(text)
            if not text:
                continue

            ctime = msg.get("create_time") or msg.get("createTime") or node.get("create_time")
            ctime_iso = _safe_dt(ctime)

            messages.append((ctime_iso, role, text))

        # Sort chronologically where possible
        messages.sort(key=lambda x: (x[0] is None, x[0] or ""))

        user_turns = sum(1 for _, role, _ in messages if role == "user")
        assistant_turns = sum(1 for _, role, _ in messages if role == "assistant")

        # Build one "document" per conversation (good for clustering)
        doc_parts = []
        if title:
            doc_parts.append(f"TITLE: {title}")
        for _, role, text in messages:
            if role:
                doc_parts.append(f"{role.upper()}: {text}")
            else:
                doc_parts.append(text)
        doc_text = "\n".join(doc_parts).strip()

        convo_rows.append(
            {
                "conversation_id": convo_id,
                "title": title,
                "create_time": create_time,
                "update_time": update_time,
                "user_turns": user_turns,
                "assistant_turns": assistant_turns,
                "doc_text": doc_text,
                "doc_len": len(doc_text),
            }
        )

        # Optional: keep a small sample of messages for dashboard drill-down
        for i, (ctime_iso, role, text) in enumerate(messages[:50]):
            sample_msg_rows.append(
                {
                    "conversation_id": convo_id,
                    "msg_index": i,
                    "create_time": ctime_iso,
                    "role": role,
                    "text": text,
                }
            )

    df_convos = pd.DataFrame(convo_rows)
    df_msgs = pd.DataFrame(sample_msg_rows)

    # Drop empty docs
    df_convos = df_convos[df_convos["doc_text"].astype(str).str.len() > 0].copy()

    return df_convos, df_msgs


# ----------------------------
# Theme modeling
# ----------------------------

def choose_k(n: int, k: Optional[int]) -> int:
    """Reasonable default number of clusters for broad categories."""
    if k is not None:
        return max(2, int(k))
    # Heuristic: broad buckets, not tiny clusters
    if n < 50:
        return 6
    if n < 200:
        return 10
    if n < 800:
        return 18
    return 25


def top_terms_per_cluster(
    vectorizer: TfidfVectorizer,
    model: KMeans,
    top_n: int = 12,
) -> Dict[int, List[str]]:
    terms = vectorizer.get_feature_names_out()
    centers = model.cluster_centers_
    out: Dict[int, List[str]] = {}
    for cluster_id in range(centers.shape[0]):
        idx = centers[cluster_id].argsort()[::-1][:top_n]
        out[cluster_id] = [terms[i] for i in idx]
    return out


def label_from_terms(terms: List[str]) -> str:
    """
    Very simple label: join a few top terms into a human-ish label.
    You’ll refine these in the dashboard anyway.
    """
    if not terms:
        return "Unlabeled"
    head = terms[:4]
    return " / ".join(head)


def run_theme_clustering(
    df_convos: pd.DataFrame,
    k: Optional[int] = None,
    min_df: int = 3,
    max_df: float = 0.5,
    max_features: int = 25000,
    ngram_max: int = 2,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, Dict[int, List[str]]]:
    docs = df_convos["doc_text"].astype(str).tolist()
    n = len(docs)
    k_final = choose_k(n, k)

    vectorizer = TfidfVectorizer(
        stop_words="english",
        min_df=min_df,
        max_df=max_df,
        max_features=max_features,
        ngram_range=(1, ngram_max),
    )
    X = vectorizer.fit_transform(docs)

    model = KMeans(n_clusters=k_final, n_init="auto", random_state=random_state)
    cluster_id = model.fit_predict(X)

    df_out = df_convos.copy()
    df_out["cluster_id"] = cluster_id

    cluster_terms = top_terms_per_cluster(vectorizer, model, top_n=14)
    df_out["cluster_label"] = df_out["cluster_id"].map(
        lambda cid: label_from_terms(cluster_terms.get(int(cid), []))
    )

    return df_out, cluster_terms


# ----------------------------
# CLI
# ----------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("conversations_json", help="Path to conversations.json from ChatGPT export")
    ap.add_argument("--outdir", default="out", help="Output directory (default: ./out)")
    ap.add_argument("--k", type=int, default=None, help="Number of clusters (default: auto)")
    ap.add_argument("--min-df", type=int, default=3, help="TF-IDF min_df (default: 3)")
    ap.add_argument("--max-df", type=float, default=0.5, help="TF-IDF max_df (default: 0.5)")
    ap.add_argument("--max-features", type=int, default=25000, help="TF-IDF max features (default: 25000)")
    ap.add_argument("--ngram-max", type=int, default=2, help="Use up to N-grams (default: 2)")
    ap.add_argument("--include-system", action="store_true", help="Include system messages")
    ap.add_argument("--include-tool", action="store_true", help="Include tool/function messages")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    df_convos, df_msgs = flatten_conversations(
        args.conversations_json,
        include_system=args.include_system,
        include_tool=args.include_tool,
    )

    if df_convos.empty:
        raise SystemExit("No conversation text found. Export format might differ; inspect your JSON.")

    df_clustered, cluster_terms = run_theme_clustering(
        df_convos,
        k=args.k,
        min_df=args.min_df,
        max_df=args.max_df,
        max_features=args.max_features,
        ngram_max=args.ngram_max,
    )

    # Write outputs
    flat_path = os.path.join(args.outdir, "conversations_flat.csv")
    msgs_path = os.path.join(args.outdir, "conversations_messages_sample.csv")
    clusters_path = os.path.join(args.outdir, "clusters.csv")
    terms_path = os.path.join(args.outdir, "cluster_terms.json")
    summary_path = os.path.join(args.outdir, "cluster_summary.csv")

    df_clustered.to_csv(flat_path, index=False)
    df_msgs.to_csv(msgs_path, index=False)

    df_clustered[["conversation_id", "title", "create_time", "update_time", "cluster_id", "cluster_label"]].to_csv(
        clusters_path, index=False
    )

    with open(terms_path, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in cluster_terms.items()}, f, ensure_ascii=False, indent=2)

    summary = (
        df_clustered.groupby(["cluster_id", "cluster_label"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    # Attach top terms to summary for convenience
    summary["top_terms"] = summary["cluster_id"].map(lambda cid: ", ".join(cluster_terms.get(int(cid), [])[:12]))
    summary.to_csv(summary_path, index=False)

    print("Wrote:")
    print(" -", flat_path)
    print(" -", msgs_path)
    print(" -", clusters_path)
    print(" -", terms_path)
    print(" -", summary_path)
    print(f"\nConversations analyzed: {len(df_clustered)}")
    print(f"Clusters: {df_clustered['cluster_id'].nunique()}")


if __name__ == "__main__":
    main()
