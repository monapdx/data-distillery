#!/usr/bin/env python3
"""
Theme miner for ChatGPT conversations.json (offline).
- Extracts text per conversation
- Clusters conversations into themes (KMeans over TF-IDF)
- Auto-labels clusters with top terms
- Saves CSV + Markdown summaries

Usage:
  python theme_miner.py input/conversations.json --k 12
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Requires: pip install scikit-learn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


STOP_EXTRA = {
    # ChatGPT-export specific filler + common chat words
    "yeah", "yep", "okay", "ok", "lol", "uh", "um", "gonna", "wanna",
    "thing", "stuff", "like", "just", "really", "actually", "basically",
    "chatgpt", "assistant", "user",
}


def clean_text(s: str) -> str:
    s = s.replace("\u0000", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_for_vectorizer(s: str) -> str:
    s = s.lower()
    # remove urls
    s = re.sub(r"https?://\S+", " ", s)
    # keep words/numbers, collapse punctuation
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def safe_get(d: Dict[str, Any], *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


@dataclass
class ConversationDoc:
    conv_id: str
    title: str
    created_ts: Optional[float]
    updated_ts: Optional[float]
    text: str  # full extracted text (already cleaned)


def parse_conversations_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "conversations" in data:
        # some exports wrap
        return data["conversations"]
    if isinstance(data, list):
        return data
    raise ValueError("Unexpected conversations.json structure (expected list or {conversations: [...]})")


def extract_message_text(msg: Dict[str, Any]) -> str:
    """
    Handles common ChatGPT export shapes:
    message["content"]["parts"] (list of strings)
    message["content"]["text"] (string)
    """
    content = msg.get("content") or {}
    if isinstance(content, dict):
        parts = content.get("parts")
        if isinstance(parts, list):
            joined = " ".join([p for p in parts if isinstance(p, str)])
            return clean_text(joined)
        text = content.get("text")
        if isinstance(text, str):
            return clean_text(text)
    # fallback: sometimes message["text"]
    if isinstance(msg.get("text"), str):
        return clean_text(msg["text"])
    return ""


def conversation_to_doc(conv: Dict[str, Any], include_assistant: bool = True) -> ConversationDoc:
    conv_id = str(conv.get("id") or conv.get("conversation_id") or "")
    title = str(conv.get("title") or "").strip() or "(untitled)"

    created_ts = conv.get("create_time") or conv.get("created_time")
    updated_ts = conv.get("update_time") or conv.get("updated_time")

    mapping = conv.get("mapping") or {}
    texts: List[str] = []

    # The export mapping is a dict of nodes. Each has a "message" and "parent"/"children".
    # We’ll just collect all messages with role user/assistant.
    for node in mapping.values():
        msg = node.get("message") if isinstance(node, dict) else None
        if not isinstance(msg, dict):
            continue

        role = safe_get(msg, "author", "role", default="")
        if role not in ("user", "assistant"):
            continue
        if (role == "assistant") and (not include_assistant):
            continue

        t = extract_message_text(msg)
        if t:
            prefix = "USER: " if role == "user" else "ASSISTANT: "
            texts.append(prefix + t)

    full = clean_text("\n".join(texts))
    return ConversationDoc(
        conv_id=conv_id,
        title=title,
        created_ts=created_ts if isinstance(created_ts, (int, float)) else None,
        updated_ts=updated_ts if isinstance(updated_ts, (int, float)) else None,
        text=full,
    )


def human_date(ts: Optional[float]) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        return ""


def auto_choose_k(n: int) -> int:
    """
    Heuristic: sqrt(n/2), clipped. Works decently for personal archives.
    """
    if n <= 10:
        return max(2, min(5, n))
    k = int(round(math.sqrt(n / 2)))
    return max(5, min(25, k))


def top_terms_for_cluster(
    vectorizer: TfidfVectorizer,
    X,
    labels: List[int],
    cluster_id: int,
    top_n: int = 12
) -> List[Tuple[str, float]]:
    import numpy as np

    idx = [i for i, lab in enumerate(labels) if lab == cluster_id]
    if not idx:
        return []
    sub = X[idx]
    # Mean TF-IDF per feature
    mean_vec = sub.mean(axis=0)
    if hasattr(mean_vec, "A1"):
        mean_arr = mean_vec.A1
    else:
        mean_arr = np.asarray(mean_vec).ravel()

    feats = vectorizer.get_feature_names_out()
    top_idx = mean_arr.argsort()[::-1][:top_n]
    out = []
    for j in top_idx:
        term = feats[j]
        score = float(mean_arr[j])
        out.append((term, score))
    return out


def write_csv(path: str, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", help="Path to conversations.json")
    ap.add_argument("--k", type=int, default=0, help="Number of themes (clusters). 0 = auto")
    ap.add_argument("--min-chars", type=int, default=600, help="Skip very short conversations below this many chars")
    ap.add_argument("--include-assistant", action="store_true", help="Include assistant messages (default: only user)")
    ap.add_argument("--outdir", default="theme_output", help="Output directory")
    args = ap.parse_args()

    convs = parse_conversations_json(args.json_path)
    docs: List[ConversationDoc] = []

    for conv in convs:
        doc = conversation_to_doc(conv, include_assistant=args.include_assistant)
        if len(doc.text) >= args.min_chars:
            docs.append(doc)

    if len(docs) < 5:
        raise SystemExit(f"Not enough conversations after filtering (kept {len(docs)}). Lower --min-chars.")

    os.makedirs(args.outdir, exist_ok=True)

    k = args.k if args.k and args.k > 1 else auto_choose_k(len(docs))

    # Vectorize
    corpus = [normalize_for_vectorizer(d.text) for d in docs]

    vectorizer = TfidfVectorizer(
        max_features=60000,
        ngram_range=(1, 2),
        stop_words="english",
        min_df=2,
    )

    X = vectorizer.fit_transform(corpus)

    # Cluster
    km = KMeans(n_clusters=k, random_state=42, n_init="auto")
    labels = km.fit_predict(X).tolist()

    # Cluster -> terms + representative titles
    cluster_terms: Dict[int, List[Tuple[str, float]]] = {}
    for cid in range(k):
        terms = top_terms_for_cluster(vectorizer, X, labels, cid, top_n=15)
        # filter some extra stopwords-ish tokens
        filtered = [(t, s) for (t, s) in terms if t not in STOP_EXTRA and len(t) > 2]
        cluster_terms[cid] = filtered[:12]

    # Build rows
    convo_rows: List[Dict[str, Any]] = []
    by_cluster: Dict[int, List[int]] = defaultdict(list)
    for i, (d, lab) in enumerate(zip(docs, labels)):
        by_cluster[lab].append(i)

    # Name clusters with top 3 terms
    cluster_name: Dict[int, str] = {}
    for cid in range(k):
        terms = [t for t, _ in cluster_terms[cid][:4]]
        if terms:
            cluster_name[cid] = " / ".join(terms[:3])
        else:
            cluster_name[cid] = f"Theme {cid}"

    for d, lab in zip(docs, labels):
        convo_rows.append({
            "conversation_id": d.conv_id,
            "title": d.title,
            "created": human_date(d.created_ts),
            "updated": human_date(d.updated_ts),
            "theme_id": lab,
            "theme_name": cluster_name[lab],
            "char_count": len(d.text),
        })

    # Write conversations_labeled.csv
    write_csv(
        os.path.join(args.outdir, "conversations_labeled.csv"),
        convo_rows,
        fieldnames=["conversation_id", "title", "created", "updated", "theme_id", "theme_name", "char_count"],
    )

    # Write clusters_top_terms.csv
    term_rows = []
    for cid in range(k):
        for rank, (term, score) in enumerate(cluster_terms[cid], start=1):
            term_rows.append({
                "theme_id": cid,
                "theme_name": cluster_name[cid],
                "rank": rank,
                "term": term,
                "score": f"{score:.6f}",
            })
    write_csv(
        os.path.join(args.outdir, "clusters_top_terms.csv"),
        term_rows,
        fieldnames=["theme_id", "theme_name", "rank", "term", "score"],
    )

    # Write themes_summary.md
    summary_path = os.path.join(args.outdir, "themes_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# ChatGPT Archive Theme Summary\n\n")
        f.write(f"- Conversations analyzed: {len(docs)} (filtered by min chars = {args.min_chars})\n")
        f.write(f"- Themes (k): {k}\n")
        f.write(f"- Include assistant text: {args.include_assistant}\n\n")

        # Sort clusters by size desc
        cluster_sizes = sorted(((cid, len(ix)) for cid, ix in by_cluster.items()), key=lambda x: x[1], reverse=True)

        for cid, size in cluster_sizes:
            f.write(f"## Theme {cid}: {cluster_name[cid]}  ({size} conversations)\n\n")
            if cluster_terms[cid]:
                f.write("Top terms: " + ", ".join([t for t, _ in cluster_terms[cid][:12]]) + "\n\n")

            # show up to 10 representative titles
            sample_idx = by_cluster[cid][:10]
            for i in sample_idx:
                d = docs[i]
                f.write(f"- {d.title} ({human_date(d.updated_ts)})\n")
            f.write("\n")

    # Optional: one markdown file per theme listing all convos
    for cid in range(k):
        path = os.path.join(args.outdir, f"theme_{cid:02d}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Theme {cid}: {cluster_name[cid]}\n\n")
            f.write("Top terms: " + ", ".join([t for t, _ in cluster_terms[cid][:12]]) + "\n\n")
            for i in sorted(by_cluster[cid], key=lambda j: (docs[j].updated_ts or 0), reverse=True):
                d = docs[i]
                f.write(f"- **{d.title}** — updated {human_date(d.updated_ts)} — id `{d.conv_id}`\n")

    print(f"Done.\nOutput directory: {os.path.abspath(args.outdir)}\n"
          f"- conversations_labeled.csv\n- clusters_top_terms.csv\n- themes_summary.md\n- theme_XX.md files")


if __name__ == "__main__":
    main()
