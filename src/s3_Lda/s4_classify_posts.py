import json
import pandas as pd
from gensim.corpora.dictionary import Dictionary
from gensim.models.ldamodel import LdaModel
from paths import NORMALIZED_POSTS, TRAINED_LDA, TRAINED_DCT, TOPIC_INFERENCE, CLASSIFIED_POSTS
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_topic_mapping(topic_inference_path: Path) -> dict:
    """Load topic names from TOPIC_INFERENCE JSON file.

    Returns a dict mapping topic_id (0-indexed) to inferred_name.
    Note: topic_inference.json uses 0-indexed topic_id, but we map it accordingly.
    """
    if not Path(topic_inference_path).exists():
        raise FileNotFoundError(
            f"Topic inference file not found at {topic_inference_path}")

    with open(str(topic_inference_path), 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Build mapping: topic_id -> inferred_name
    topic_mapping = {}
    for topic in data.get('topics', []):
        topic_id = topic.get('topic_id')
        inferred_name = topic.get('inferred_name')
        if topic_id is not None and inferred_name is not None:
            topic_mapping[topic_id] = inferred_name

    return topic_mapping


def classify_posts(model: LdaModel, posts_df: pd.DataFrame, topic_mapping: dict) -> pd.DataFrame:
    """Classify posts to their most probable topic based on LDA model.

    For each post's normalized text, get the most probable topic from the model,
    then map to the inferred topic name from topic_mapping.

    Args:
        model: Trained LDA model
        posts_df: DataFrame with 'normalized_text' column (space-separated tokens)
        topic_mapping: Dict mapping topic_id (0-indexed) to inferred_name

    Returns:
        DataFrame with added 'topic' column containing inferred topic names.
    """
    result_df = posts_df.copy()
    topics = []

    for idx, row in posts_df.iterrows():
        normalized_text = row.get('normalized_text', '')

        if not normalized_text or not isinstance(normalized_text, str):
            topics.append(None)
            continue

        # Tokenize the normalized text (space-separated)
        tokens = normalized_text.split()

        if not tokens:
            topics.append(None)
            continue

        # Get topic distribution for this document
        # First convert to bow using the model's dictionary
        bow = model.id2word.doc2bow(tokens)

        if not bow:
            topics.append(None)
            continue

        # Get topic distribution: list of (topic_id, probability) tuples
        doc_topics = model.get_document_topics(bow)

        if not doc_topics:
            topics.append(None)
            continue

        # Find the most probable topic (highest probability)
        most_probable_topic_id = max(doc_topics, key=lambda x: x[1])[0]

        # Map to inferred name (topic_id is 0-indexed in model, matches topic_mapping keys)
        topic_name = topic_mapping.get(
            most_probable_topic_id, f"Unknown Topic {most_probable_topic_id}")
        topics.append(topic_name)

    result_df['topic'] = topics
    return result_df


def main():
    """Main pipeline: load model, load posts, classify to topics, save results."""

    # Load LDA model and dictionary
    if not Path(TRAINED_LDA).exists():
        raise FileNotFoundError(
            f"Trained LDA model not found at {TRAINED_LDA}")

    if not Path(TRAINED_DCT).exists():
        raise FileNotFoundError(
            f"Trained dictionary not found at {TRAINED_DCT}")

    print(f"Loading trained LDA model from {TRAINED_LDA}")
    model = LdaModel.load(str(TRAINED_LDA))
    dictionary = Dictionary.load(str(TRAINED_DCT))
    print(f"Model loaded. Number of topics: {model.num_topics}")

    # Load topic inference mapping
    print(f"Loading topic names from {TOPIC_INFERENCE}")
    topic_mapping = load_topic_mapping(Path(TOPIC_INFERENCE))
    print(f"Loaded {len(topic_mapping)} topic names")

    # Load normalized posts
    if not Path(NORMALIZED_POSTS).exists():
        raise FileNotFoundError(
            f"Normalized posts not found at {NORMALIZED_POSTS}")

    print(f"Loading normalized posts from {NORMALIZED_POSTS}")
    posts_df = pd.read_csv(str(NORMALIZED_POSTS))
    print(f"Loaded {len(posts_df)} posts")

    # Classify posts
    print("Classifying posts to topics...")
    classified_df = classify_posts(model, posts_df, topic_mapping)

    # Save classified posts
    Path(CLASSIFIED_POSTS).parent.mkdir(parents=True, exist_ok=True)
    classified_df.to_csv(str(CLASSIFIED_POSTS), index=False)
    print(f"Classified posts saved to {CLASSIFIED_POSTS}")

    # Print summary
    print("\n=== Classification Summary ===")
    print(f"Total posts classified: {len(classified_df)}")
    print(f"Posts with valid topic: {classified_df['topic'].notna().sum()}")
    print(f"Posts with no topic: {classified_df['topic'].isna().sum()}")
    print("\nTopic distribution:")
    print(classified_df['topic'].value_counts())


if __name__ == '__main__':
    main()
