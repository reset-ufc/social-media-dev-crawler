import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import FILTRED_POSTS, NORMALIZED_POSTS
import re
from typing import List
import pandas as pd
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
import warnings
import spacy
from nltk.corpus import stopwords
from gensim.models.phrases import Phrases, Phraser

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def _ensure_spacy_model():
    try:
        spacy.load('en_core_web_sm')
    except OSError:
        import subprocess
        subprocess.check_call(
            [sys.executable, '-m', 'spacy', 'download', 'en_core_web_sm'])


_ensure_spacy_model()

# Disable parser + ner for speed
_NLP = spacy.load('en_core_web_sm', disable=['ner', 'parser'])

# Stopwords = spaCy + NLTK
_STOPWORDS = set(stopwords.words("english"))
_STOPWORDS.update(spacy.lang.en.stop_words.STOP_WORDS)


# Extend stop words
STACKEXCHANGE_STOPWORDS = {
    "answer", "question", "post", "comment", "comments", "reply", "replies",
    "op", "edit", "edited", "link", "links", "thread", "update", "updates",
    "solution", "issue", "issues", "discussion", "discussions"
}
DISCOURSE_STOPWORDS = {
    "work", "works", "working",
    "find", "found", "finding",
    "use", "uses", "using", "used",
    "make", "makes", "made",
    "get", "gets", "getting", "got",
    "try", "tries", "trying",
    "know", "knows", "knowing",
    "need", "needs", "needed",
    "want", "wants", "wanted",
    "good", "better", "best",
    "thing", "things",
    "point", "points",
    "problem", "problems",
    "case", "cases",
    "example", "examples",
    "people", "someone", "anyone", "everyone"
}

_STOPWORDS.update(STACKEXCHANGE_STOPWORDS)
_STOPWORDS.update(DISCOURSE_STOPWORDS)


ALLOWED_POS = {"NOUN", "VERB", "ADJ", "ADV"}


def strip_html_and_remove_code(text: str) -> str:
    """Remove code blocks, code tags, script/style, math-container spans, 
    inline code, fenced blocks, and images.
    Keep text inside <a>, but remove URLs.
    """

    if not isinstance(text, str) or not text:
        return ""

    # Remove fenced code blocks and inline backticks
    text = re.sub(r'```[\s\S]*?```', ' ', text)
    text = re.sub(r'`[^`]*`', ' ', text)

    # Try HTML parse
    try:
        soup = BeautifulSoup(text, "html.parser")
    except Exception:
        cleaned = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", cleaned).strip()

    # Remove math-container spans entirely
    for tag in soup.find_all("span", class_="math-container"):
        tag.decompose()

    # Remove code/pre/script/style/img entirely
    for tag_name in ("code", "pre", "script", "style", "img"):
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Preserve link text but remove the URL
    for a in soup.find_all("a"):
        a.replace_with(a.get_text(" "))

    cleaned = soup.get_text(separator=" ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


import string

PUNCT_TO_REMOVE = string.punctuation.replace("_", "").replace("-", "")


def tokenize_and_lemmatize(text: str) -> List[str]:
    """
    Tokenize, lemmatize, and filter text.
    Returns a list of normalized tokens.
    """
    text = strip_html_and_remove_code(text)
    if not text:
        return []
    
    # Remove common punctuation from text
    text = text.translate(str.maketrans("", "", PUNCT_TO_REMOVE))

    doc = _NLP(text)

    tokens = []
    for t in doc:
        lemma = t.lemma_.lower()

        # --- Kill spaCy's bad lemmatization of "data" -> "datum"
        if lemma == "datum":
            continue

        # Skip purely numeric tokens
        if lemma.isnumeric():
            continue

        # Skip tokens that are only punctuation
        if all(ch in PUNCT_TO_REMOVE for ch in lemma):
            continue

        # Drop weak verbs that survived stopword filtering
        if t.pos_ == "VERB" and lemma in DISCOURSE_STOPWORDS:
            continue

        # Keep only allowed POS tags and non-stopwords
        # Also filter out very short tokens (less than 2 chars)
        if (
            t.pos_ in ALLOWED_POS
            and lemma not in _STOPWORDS
            and len(lemma) >= 2
        ):
            tokens.append(lemma)

    return tokens


def normalize_corpora_from_posts(df: pd.DataFrame, body_field: str = 'body') -> pd.DataFrame:
    """
    Normalize a corpus of posts by tokenizing, lemmatizing, and creating bigrams/trigrams.
    
    Args:
        df: DataFrame containing posts
        body_field: Name of the column containing text to normalize
        
    Returns:
        DataFrame with added 'normalized' column containing lists of tokens
    """
    if body_field not in df.columns:
        raise ValueError(f"DataFrame does not contain body field '{body_field}'")

    df = df.copy()
    df[body_field] = df[body_field].fillna("").astype(str)

    # Tokenize + lemmatize
    print("Tokenizing and lemmatizing...")
    token_lists = df[body_field].map(tokenize_and_lemmatize)

    # IMPROVEMENT: Filter out empty token lists
    valid_tokens = [toks for toks in token_lists if len(toks) > 0]
    
    if len(valid_tokens) == 0:
        print("WARNING: No valid tokens found after normalization!")
        df["normalized"] = [[] for _ in range(len(df))]
        return df

    # Build bigrams and trigrams
    print("Building bigrams and trigrams...")
    bigram = Phrases(valid_tokens, min_count=5, threshold=10)  # IMPROVEMENT: Added thresholds
    trigram = Phrases(bigram[valid_tokens], min_count=5, threshold=10)

    bigram_mod = Phraser(bigram)
    trigram_mod = Phraser(trigram)

    # Apply bigrams and trigrams to all token lists (including empty ones)
    token_lists = [
        trigram_mod[bigram_mod[toks]] if len(toks) > 0 else []
        for toks in token_lists
    ]

    df["normalized"] = token_lists
    return df


def main():
    """
    Main processing pipeline:
    1. Load filtered posts
    2. Combine title + body
    3. Normalize text (tokenize, lemmatize, create n-grams)
    4. Save normalized text without original title/body columns
    """
    if not FILTRED_POSTS.exists():
        raise FileNotFoundError(f"Filtered posts not found at {FILTRED_POSTS}")

    print(f"Loading posts from {FILTRED_POSTS}...")
    df = pd.read_csv(str(FILTRED_POSTS))
    print(f"Loaded {len(df)} posts")

    # Combine title + body into a temporary field
    print("Combining title and body...")
    df["title"] = df["title"].fillna("") if "title" in df.columns else ""
    df["body"] = df["body"].fillna("")
    df["combined_text"] = df["title"] + " " + df["body"]

    # Normalize the combined text
    print("Normalizing text...")
    result_df = normalize_corpora_from_posts(df, body_field="combined_text")

    # Convert token lists to whitespace-separated strings
    print("Converting tokens to text...")
    out_df = result_df.copy()
    out_df["normalized_text"] = out_df["normalized"].apply(lambda t: " ".join(t))
    
    # Keep only essential columns (remove title, body, combined_text, and normalized list)
    columns_to_drop = ["title", "body", "combined_text", "normalized"]
    columns_to_keep = [col for col in out_df.columns if col not in columns_to_drop]
    out_df = out_df[columns_to_keep]

    # IMPROVEMENT: Add statistics
    empty_docs = (out_df["normalized_text"] == "").sum()
    print(f"\nNormalization complete:")
    print(f"  Total documents: {len(out_df)}")
    print(f"  Empty normalized texts: {empty_docs}")
    print(f"  Valid normalized texts: {len(out_df) - empty_docs}")

    # Save to CSV
    print(f"\nSaving to {NORMALIZED_POSTS}...")
    out_df.to_csv(str(NORMALIZED_POSTS), index=False)
    print("Done!")


if __name__ == "__main__":
    main()