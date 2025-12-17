# streamlit_app.py
"""
Streamlit Word Lab
------------------
Upload TXT/PDF/HTML (or paste text), then:
  • Extract hyphenated words (min 1 or 2+ hyphens)
  • Extract proper nouns/entities (rule-based or spaCy)
  • Explore word frequencies
  • Generate a word cloud (with stopword removal)
  • Download CSVs

Quick start:
  1) pip install -r requirements.txt
  2) streamlit run streamlit_app.py
"""

import io
import re
from pathlib import Path
from typing import List, Tuple, Optional

import pandas as pd
import streamlit as st

# Optional imports guarded so the app still runs without them
try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None  # type: ignore

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text  # type: ignore
except Exception:
    pdfminer_extract_text = None  # type: ignore

try:
    import PyPDF2  # type: ignore
except Exception:
    PyPDF2 = None  # type: ignore

# Optional spaCy NER (loaded lazily)
try:
    import spacy  # type: ignore
except Exception:
    spacy = None  # type: ignore

# Optional Word Cloud deps
try:
    from wordcloud import WordCloud, STOPWORDS  # type: ignore
except Exception:
    WordCloud = None  # type: ignore
    STOPWORDS = set()  # type: ignore

try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception:
    plt = None  # type: ignore

# -----------------------------
# Helpers
# -----------------------------

def _safe_decode_txt(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="ignore")

def _extract_text_from_pdf(file_bytes: bytes) -> str:
    # Try pdfminer first
    if pdfminer_extract_text is not None:
        try:
            with io.BytesIO(file_bytes) as bio:
                return pdfminer_extract_text(bio) or ""
        except Exception:
            pass
    # Fallback: PyPDF2
    if PyPDF2 is not None:
        try:
            text_parts: List[str] = []
            with io.BytesIO(file_bytes) as bio:
                reader = PyPDF2.PdfReader(bio)
                for page in reader.pages:
                    try:
                        text_parts.append(page.extract_text() or "")
                    except Exception:
                        continue
            return "\n".join(text_parts).strip()
        except Exception:
            pass
    return ""

def _strip_html_naive(html: str) -> str:
    html = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?>.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()

def _extract_text_from_html(file_bytes: bytes) -> str:
    raw = _safe_decode_txt(file_bytes)
    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(raw, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator=" ")
            return re.sub(r"\s+", " ", text).strip()
        except Exception:
            pass
    return _strip_html_naive(raw)

def load_text_from_upload(upload) -> Tuple[str, str]:
    filename = getattr(upload, "name", "uploaded")
    suffix = Path(filename).suffix.lower()
    data = upload.read()
    if suffix in {".txt", ".md", ".csv", ".log"}:
        return _safe_decode_txt(data), f"TXT: {filename}"
    if suffix == ".pdf":
        return _extract_text_from_pdf(data), f"PDF: {filename}"
    if suffix in {".html", ".htm"}:
        return _extract_text_from_html(data), f"HTML: {filename}"
    return _safe_decode_txt(data), f"(treated as text) {filename}"

def normalize_text(text: str) -> str:
    text = text.replace("\u2013", "-").replace("\u2014", "-")  # en/em dashes → hyphen
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def find_hyphenated_words(text: str, min_hyphens: int = 1) -> List[str]:
    pattern = re.compile(r"\b[\w']+(?:-[\w']+){" + str(min_hyphens) + r",}\b", re.IGNORECASE)
    matches = pattern.findall(text)
    seen = {}
    for m in matches:
        key = m.lower()
        if key not in seen:
            seen[key] = m
    return list(seen.values())

def word_frequencies(text: str, min_len: int = 1) -> pd.DataFrame:
    tokens = re.findall(r"[A-Za-z']+", text)
    tokens = [t.lower() for t in tokens if len(t) >= min_len]
    ser = pd.Series(tokens)
    freq = ser.value_counts().reset_index()
    freq.columns = ["word", "count"]
    return freq

# -------- Proper Noun / Entity Extraction --------
_SPACY_MODEL_CACHE: Optional[object] = None
_DEF_ENTITY_LABELS = ["PERSON", "GPE", "LOC", "ORG", "FAC"]
_DEF_JOINERS = {"of", "the", "and", "&", "de", "la", "da", "van", "der", "von", "St.", "Saint"}
_COMMON_SINGLETON_STOP = {
    "The", "A", "An", "This", "That", "It", "We", "You", "He", "She", "They",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
}

def _load_spacy_model() -> Optional[object]:
    global _SPACY_MODEL_CACHE
    if _SPACY_MODEL_CACHE is not None:
        return _SPACY_MODEL_CACHE
    if spacy is None:
        return None
    try:
        _SPACY_MODEL_CACHE = spacy.load("en_core_web_sm")
        return _SPACY_MODEL_CACHE
    except Exception:
        return None

def extract_entities_spacy(text: str, wanted: Optional[List[str]] = None) -> pd.DataFrame:
    nlp = _load_spacy_model()
    if nlp is None:
        return pd.DataFrame(columns=["entity", "label", "count"])
    labs = set(wanted or _DEF_ENTITY_LABELS)
    doc = nlp(text)
    ents = [(ent.text.strip(), ent.label_) for ent in doc.ents if ent.label_ in labs]
    if not ents:
        return pd.DataFrame(columns=["entity", "label", "count"])
    df = (pd.DataFrame(ents, columns=["entity", "label"])
            .groupby(["entity", "label"], as_index=False).size()
            .rename(columns={"size": "count"})
            .sort_values(["count", "entity"], ascending=[False, True]))
    return df

def extract_proper_nouns_rule(text: str) -> pd.DataFrame:
    token_re = r"(?:[A-Z][a-z]+(?:'[A-Za-z]+)?|[A-Z]{2,}|Mc[A-Z][a-z]+|O'[A-Z][a-z]+)"
    join_re  = r"(?:\s+(?:" + "|".join(map(re.escape, _DEF_JOINERS)) + r"))?"
    pattern  = re.compile(rf"\b{token_re}(?:{join_re}\s+{token_re})*\b")

    matches: List[str] = []
    for m in re.finditer(pattern, text):
        span = m.group().strip()
        if " " not in span and span in _COMMON_SINGLETON_STOP:
            continue
        if span.isupper() and len(span) < 3:
            continue
        matches.append(span)

    if not matches:
        return pd.DataFrame(columns=["entity", "label", "count"])

    df = pd.Series(matches).value_counts().reset_index()
    df.columns = ["entity", "count"]
    df["label"] = "proper_noun"
    return df[["entity", "label", "count"]].sort_values(["count", "entity"], ascending=[False, True])

def to_csv_download(df: pd.DataFrame, filename: str, label: str):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label=label, data=csv, file_name=filename, mime="text/csv")

# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="Streamlit Word Lab", page_icon="🧪", layout="wide")
st.title("🧪 Streamlit Word Lab")
st.caption("Upload text/PDF/HTML, mine hyphenated words, explore frequencies, extract names/places, make a word cloud, and export.")

with st.sidebar:
    st.header("Input")
    uploaded_files = st.file_uploader(
        "Upload TXT / PDF / HTML files (you can select multiple)",
        type=["txt", "md", "csv", "log", "pdf", "html", "htm"],
        accept_multiple_files=True,
    )
    pasted = st.text_area("…or paste text here", height=160, placeholder="Paste text…")
    st.divider()
    st.markdown("**Hyphenated-word settings**")
    min_hyphens = st.radio(
        "Minimum number of hyphens in a word",
        options=[1, 2],
        index=0,
        help="Pick 1 to find any hyphenated words; pick 2 for two-or-more hyphens.",
    )
    min_token_len = st.slider("Min token length for frequencies", 1, 10, 2)

# Gather text
sources: List[str] = []
texts: List[str] = []

if uploaded_files:
    for f in uploaded_files:
        txt, label = load_text_from_upload(f)
        if txt:
            texts.append(txt)
        sources.append(label)

if pasted.strip():
    texts.append(pasted)
    sources.append("pasted text")

raw_text = "\n\n".join(texts).strip()

if not raw_text:
    st.info("👋 Start by uploading a file or pasting text in the sidebar.")
    st.stop()

text = normalize_text(raw_text)

st.subheader("Sources")
if sources:
    st.write(" • ".join(sources))

# Tabs
hy_tab, freq_tab, ent_tab, wc_tab, view_tab = st.tabs(
    ["Hyphenated Words", "Frequencies", "Proper Nouns / Entities", "Word Cloud", "View Text"]
)

with hy_tab:
    st.markdown("### Hyphenated Words")
    hy_words = find_hyphenated_words(text, min_hyphens=min_hyphens)
    if hy_words:
        df_hy = pd.DataFrame({"hyphenated_word": sorted(hy_words, key=str.lower)})
        st.dataframe(df_hy, use_container_width=True, hide_index=True)
        to_csv_download(df_hy, filename=f"hyphenated_min{min_hyphens}.csv", label="⬇️ Download hyphenated words (CSV)")
        st.success(f"Found {len(df_hy)} unique hyphenated words (min hyphens = {min_hyphens}).")
    else:
        st.warning("No hyphenated words found with current settings.")

with freq_tab:
    st.markdown("### Word Frequencies")
    df_freq = word_frequencies(text, min_len=min_token_len)
    st.dataframe(df_freq, use_container_width=True)
    to_csv_download(df_freq, filename="word_frequencies.csv", label="⬇️ Download frequencies (CSV)")

with ent_tab:
    st.markdown("### Proper Nouns / Named Entities")
    use_spacy_ui = st.checkbox("Use spaCy NER if available", value=True, key="ents_spacy")
    if use_spacy_ui:
        chosen_labels_ui = st.multiselect(
            "Entity labels", _DEF_ENTITY_LABELS, default=_DEF_ENTITY_LABELS, key="ents_labels",
            help="We'll keep only these labels when using spaCy.")
    else:
        chosen_labels_ui = []

    ents_df = pd.DataFrame()
    used_spacy = False
    if use_spacy_ui:
        ents_df = extract_entities_spacy(text, wanted=chosen_labels_ui)
        used_spacy = not ents_df.empty
    if ents_df.empty:
        ents_df = extract_proper_nouns_rule(text)

    if ents_df.empty:
        st.info("No proper nouns/entities found.")
    else:
        st.dataframe(ents_df, use_container_width=True)
        to_csv_download(ents_df, filename="entities.csv", label="⬇️ Download entities (CSV)")
        st.caption(("spaCy NER" if used_spacy else "Rule-based extractor")
                   + f" found {ents_df.shape[0]} unique items.")

with wc_tab:
    st.markdown("### Word Cloud")
    if WordCloud is None or plt is None:
        st.info("To enable word clouds, install dependencies: `pip install wordcloud matplotlib`.")
    else:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            max_words = st.slider("Max words", 50, 1000, 200, step=50)
        with col2:
            min_len_wc = st.slider("Min word length", 1, 10, 3)
        with col3:
            transparent = st.checkbox("Transparent background", value=True)
        extra_sw = st.text_area("Extra stopwords (comma or space separated)", placeholder="e.g. said, mr, mrs, like")

        # Build stopword set
        sw = set(STOPWORDS) if isinstance(STOPWORDS, set) else set(STOPWORDS)
        sw.update(w.strip().lower() for w in re.split(r"[\\s,]+", extra_sw) if w.strip())

        # Tokenize + filter
        tokens = re.findall(r"[A-Za-z']+", text)
        tokens = [t.lower() for t in tokens if len(t) >= min_len_wc and t.lower() not in sw]

        if not tokens:
            st.warning("No tokens available after stopword/length filtering.")
        else:
            freqs = pd.Series(tokens).value_counts().to_dict()
            wc = WordCloud(
                width=1200, height=600, max_words=max_words,
                background_color=None if transparent else "white",
                mode="RGBA" if transparent else "RGB"
            ).generate_from_frequencies(freqs)
            fig = plt.figure(figsize=(10, 5))
            plt.imshow(wc, interpolation="bilinear")
            plt.axis("off")
            st.pyplot(fig, clear_figure=True)

with view_tab:
    st.markdown("### Clean Text Preview")
    st.text_area("Text", value=text[:20000], height=300)
    st.caption("Showing up to first 20,000 characters for performance.")

st.divider()
st.markdown(
    """
**Tips**
- PDFs that are scans (images) need OCR (e.g., Tesseract) before this app can read text.
- If hyphenated words look odd, they may be soft-hyphen artifacts; this app normalizes en/em dashes to hyphens.
- For best entity accuracy, install **spaCy** and its model: `pip install spacy` then `python -m spacy download en_core_web_sm`.
- The Word Cloud uses the `wordcloud` library’s default English stopwords; add your own in the UI. Toggle **Transparent background** for easy overlay/sharing.
"""
)
