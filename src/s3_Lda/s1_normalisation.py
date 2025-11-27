import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk
import warnings
from bs4 import MarkupResemblesLocatorWarning
from bs4 import BeautifulSoup
import pandas as pd
from typing import List
import re
from paths import PREPROCESSED_POSTS, NORMALIZED_POSTS



# Suppress BeautifulSoup warning when content resembles a URL
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def _ensure_nltk_resources():
    try:
        stopwords.words('english')
        _ = WordNetLemmatizer()
    except (LookupError, OSError):
        nltk.download('stopwords')
        nltk.download('wordnet')


_ensure_nltk_resources()

_STOPWORDS = set(stopwords.words('english'))


def tokenize(text: str) -> List[str]:
    # first strip HTML and remove code/link/image blocks
    text = strip_html_and_remove_code(text)
    if not isinstance(text, str) or not text:
        return []
    # extract words (alphanumeric + underscore), ignore single punctuation
    tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
    return tokens


def strip_html_and_remove_code(text: str) -> str:
    """Remove code blocks, inline code, links and images; strip remaining HTML tags.

    - Remove fenced code blocks (``` ```), inline backtick code (`...`).
    - Remove entirely the tags and their contents for: `code`, `pre`, `script`, `style`, `img`, `a`.
    - For other tags, remove the tags but keep their text.
    """
    if not isinstance(text, str) or not text:
        return ''

    # Remove fenced code blocks and inline backtick code first
    text = re.sub(r'```[\s\S]*?```', ' ', text)
    text = re.sub(r'`[^`]*`', ' ', text)

    # Parse HTML and remove specific tags and their contents
    try:
        soup = BeautifulSoup(text, 'html.parser')
    except Exception:
        # fallback: strip tags with regex if parsing fails
        cleaned = re.sub(r'<[^>]+>', ' ', text)
        return re.sub(r'\s+', ' ', cleaned).strip()

    # Remove tags whose content should be discarded entirely
    for tag_name in ('code', 'pre', 'script', 'style', 'img', 'a'):
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Get cleaned text (joins remaining text nodes)
    cleaned = soup.get_text(separator=' ')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def normalize_tokens(tokens: List[str]) -> List[str]:
    lemma = WordNetLemmatizer()
    processed = [t.replace('-', '_') for t in tokens]
    processed = [t for t in processed if not t.isdigit()]
    processed = [t for t in processed if re.match(r'^[A-Za-z0-9_]+$', t)]
    processed = [lemma.lemmatize(t) for t in processed]
    processed = [t for t in processed if t not in _STOPWORDS and len(t) > 1]
    return processed


def normalize_corpora_from_posts(df: pd.DataFrame, body_field: str = 'body') -> pd.DataFrame:
    """Normalize the text in `body_field` for all rows in `df`.

    Returns a new DataFrame with a column `normalized` containing a list of tokens for LDA.
    """
    if body_field not in df.columns:
        raise ValueError(
            f"DataFrame does not contain body field '{body_field}'")

    tokens_series = df[body_field].fillna('').astype(str).map(tokenize)
    normalized = tokens_series.map(normalize_tokens)
    normalized = normalized.map(lambda x: x if x else [])
    result_df = df.copy()
    result_df['normalized'] = normalized
    return result_df


def main():
    if not PREPROCESSED_POSTS.exists():
        raise FileNotFoundError(
            f"Preprocessed posts not found at {PREPROCESSED_POSTS}")

    df = pd.read_csv(str(PREPROCESSED_POSTS))
    result_df = normalize_corpora_from_posts(df, body_field='body')

    # Save normalized posts. Store tokens as space-joined string to keep CSV simple.
    out_df = result_df.copy()
    out_df['normalized_text'] = out_df['normalized'].apply(
        lambda toks: ' '.join(toks))
    # keep all original columns plus normalized and normalized_text
    out_df.to_csv(str(NORMALIZED_POSTS), index=False)


if __name__ == '__main__':
    main()
