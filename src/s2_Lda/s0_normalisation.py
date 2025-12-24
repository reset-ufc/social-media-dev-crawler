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
    text = strip_html_and_remove_code(text)
    if not text:
        return []
    
    # remove sinais comuns de pontuação do texto
    text = text.translate(str.maketrans("", "", PUNCT_TO_REMOVE))

    doc = _NLP(text)

    tokens = []
    for t in doc:
        lemma = t.lemma_.lower()

        # remover tokens puramente numéricos
        if lemma.isnumeric():
            continue

        # remover tokens só de pontuação
        if all(ch in PUNCT_TO_REMOVE for ch in lemma):
            continue

        if (
            t.pos_ in ALLOWED_POS
            and lemma not in _STOPWORDS
        ):
            tokens.append(lemma)

    return tokens


def normalize_corpora_from_posts(df: pd.DataFrame, body_field: str = 'body') -> pd.DataFrame:
    if body_field not in df.columns:
        raise ValueError(f"DataFrame does not contain body field '{body_field}'")

    df = df.copy()
    df[body_field] = df[body_field].fillna("").astype(str)

    # Tokenize + lemmatize
    token_lists = df[body_field].map(tokenize_and_lemmatize)

    # -----------------------------------------------------------------------
    # Bigrams + Trigrams
    # -----------------------------------------------------------------------
    bigram = Phrases(token_lists)
    trigram = Phrases(bigram[token_lists])

    bigram_mod = Phraser(bigram)
    trigram_mod = Phraser(trigram)

    token_lists = [trigram_mod[bigram_mod[toks]] for toks in token_lists]

    df["normalized"] = token_lists
    return df


def main():
    if not FILTRED_POSTS.exists():
        raise FileNotFoundError(f"Filtered posts not found at {FILTRED_POSTS}")

    df = pd.read_csv(str(FILTRED_POSTS))

    # Combine title + body
    if "title" in df.columns:
        df["title"] = df["title"].fillna("")
        df["body"] = df["body"].fillna("")
        df["body"] = df["title"] + " " + df["body"]

    result_df = normalize_corpora_from_posts(df, body_field="body")

    # Save tokens as whitespace-joined text
    out_df = result_df.copy()
    out_df["normalized_text"] = out_df["normalized"].apply(lambda t: " ".join(t))

    out_df.to_csv(str(NORMALIZED_POSTS), index=False)


if __name__ == "__main__":
    main()
