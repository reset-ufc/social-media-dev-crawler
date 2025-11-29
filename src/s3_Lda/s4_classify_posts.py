import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
from gensim.corpora.dictionary import Dictionary
from gensim.models.ldamodel import LdaModel
from paths import *



def load_topic_mapping(topic_inference_path: Path) -> dict:
    """Load topic names from TOPIC_INFERENCE JSON file using pandas.

    Returns a dict mapping topic_id (0-indexed) to inferred_name.
    """
    if not Path(topic_inference_path).exists():
        raise FileNotFoundError(
            f"Topic inference file not found at {topic_inference_path}")

    with open(str(topic_inference_path), 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'topics' not in data:
        return {}

    topics_df = pd.DataFrame(data['topics'])

    id_col = None
    if 'topic_id' in topics_df.columns:
        id_col = 'topic_id'
    elif 'topic_index' in topics_df.columns:
        id_col = 'topic_index'

    name_col = None
    if 'inferred_name' in topics_df.columns:
        name_col = 'inferred_name'
    elif 'topic_name' in topics_df.columns:
        name_col = 'topic_name'
    
    if id_col is None or name_col is None:
        print(f"Warning: Could not find topic ID or name columns in {topic_inference_path}. Topic names will be unknown.")
        return {}

    topic_mapping = topics_df.set_index(id_col)[name_col].to_dict()

    return topic_mapping


def classify_posts(model: LdaModel, posts_df: pd.DataFrame, topic_mapping: dict) -> pd.DataFrame:
    """
    Classifies post groups to their most probable topic and stores:
    - dominant topic
    - dominant topic contribution percentage (Topic_Perc_Contrib)
    """
    result_df = posts_df.copy()
    
    # Initialize both new columns
    result_df['topic'] = pd.NA
    result_df['topic_perc_contrib'] = pd.NA

    grouped = result_df.groupby(['site', 'question_id'])

    for name, group in grouped:
        texts_to_join = group['normalized_text'].dropna().astype(str)
        if texts_to_join.empty:
            continue

        combined_text = ' '.join(texts_to_join)
        tokens = combined_text.split()
        bow = model.id2word.doc2bow(tokens)
        doc_topics = model.get_document_topics(bow)

        most_probable_topic_id, most_probable_topic_percentage = max(doc_topics, key=lambda x: x[1])
        topic_name = topic_mapping.get(most_probable_topic_id, most_probable_topic_id)

        question_post_index = group[group['type'] == 'question'].index
        if not question_post_index.empty:
            result_df.loc[question_post_index, 'topic'] = topic_name
            result_df.loc[question_post_index, 'topic_perc_contrib'] = most_probable_topic_percentage

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

    # Print summary for question posts only
    question_posts_df = classified_df[classified_df['type'] == 'question']

    print("\n=== Classification Summary (Questions Only) ===")
    print(f"Total questions: {len(question_posts_df)}")
    print(f"Questions with valid topic: {question_posts_df['topic'].notna().sum()}")
    print(f"Questions with no topic: {question_posts_df['topic'].isna().sum()}")
    print("\nTopic distribution (Questions Only):")
    print(question_posts_df['topic'].value_counts())


if __name__ == '__main__':
    print(load_topic_mapping(TOPIC_INFERENCE))
