import json
import pandas as pd
from gensim.corpora.dictionary import Dictionary
from gensim.models.ldamodel import LdaModel
from paths import *
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
        print(
            f"Warning: Could not find topic ID or name columns in {topic_inference_path}. Topic names will be unknown.")
        return {}

    topic_mapping = topics_df.set_index(id_col)[name_col].to_dict()

    return topic_mapping


def classify_posts(model: LdaModel, posts_df: pd.DataFrame, topic_mapping: dict, main_topic=None) -> pd.DataFrame:
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

        most_probable_topic_id, most_probable_topic_percentage = max(
            doc_topics, key=lambda x: x[1])
        topic_name = topic_mapping.get(
            most_probable_topic_id, most_probable_topic_id)

        question_post_index = group[group['type'] == 'question'].index
        if not question_post_index.empty:
            result_df.loc[question_post_index, 'topic'] = topic_name
            result_df.loc[question_post_index,
                          'topic_perc_contrib'] = most_probable_topic_percentage

    return result_df


def classify_posts_subtopic(model: LdaModel, posts_df: pd.DataFrame, topic_mapping: dict, main_topic: str) -> pd.DataFrame:
    """
    Classifies post groups within a specific main topic to subtopics.
    Only processes posts where 'topic' == main_topic.
    Adds 'subtopic' column with the inferred subtopic names.
    Adds 'subtopic_perc_contrib' column with the subtopic contribution percentage.
    """
    result_df = posts_df.copy()

    # Initialize subtopic columns
    result_df['subtopic'] = pd.NA
    result_df['subtopic_perc_contrib'] = pd.NA

    # Filter only posts with the specified main topic
    main_topic_mask = result_df['topic'] == main_topic

    grouped = result_df[main_topic_mask].groupby(['site', 'question_id'])

    for name, group in grouped:
        texts_to_join = group['normalized_text'].dropna().astype(str)
        if texts_to_join.empty:
            continue

        combined_text = ' '.join(texts_to_join)
        tokens = combined_text.split()
        bow = model.id2word.doc2bow(tokens)
        doc_topics = model.get_document_topics(bow)

        if not doc_topics:
            continue

        most_probable_topic_id, most_probable_topic_percentage = max(
            doc_topics, key=lambda x: x[1])
        subtopic_name = topic_mapping.get(
            most_probable_topic_id, most_probable_topic_id)

        question_post_index = group[group['type'] == 'question'].index
        if not question_post_index.empty:
            result_df.loc[question_post_index, 'subtopic'] = subtopic_name
            result_df.loc[question_post_index,
                          'subtopic_perc_contrib'] = most_probable_topic_percentage

    return result_df


def main_classify_main_topics(model_path):
    """Classify all normalized posts into main topics.

    Loads the trained LDA model, normalizes posts, and assigns each post
    to its most probable topic.
    """
    # Load LDA model and dictionary
    if not Path(model_path / TRAINED_LDA).exists():
        raise FileNotFoundError(
            f"Trained LDA model not found at {model_path / TRAINED_LDA}")

    if not Path(model_path / TRAINED_DCT).exists():
        raise FileNotFoundError(
            f"Trained dictionary not found at {model_path / TRAINED_DCT}")

    print(f"Loading trained LDA model from {model_path / TRAINED_LDA}")
    model = LdaModel.load(str(model_path / TRAINED_LDA))
    print(f"Model loaded. Number of topics: {model.num_topics}")

    print(f"Loading topic names from {model_path / 'topic_inference.json'}")
    topic_mapping = load_topic_mapping(
        Path(model_path / 'topic_inference.json'))
    print(f"Loaded {len(topic_mapping)} topic names")

    # Load normalized posts
    if not Path(NORMALIZED_POSTS).exists():
        raise FileNotFoundError(
            f"Normalized posts not found at {NORMALIZED_POSTS}")

    print(f"Loading normalized posts from {NORMALIZED_POSTS}")
    df = pd.read_csv(str(NORMALIZED_POSTS))
    print(f"Loaded {len(df)} posts")

    # Classify posts to main topics
    print("Classifying posts to main topics...")
    classified_df = classify_posts(model, df, topic_mapping)

    # Save classified posts
    Path(CLASSIFIED_POSTS).parent.mkdir(parents=True, exist_ok=True)
    classified_df.to_csv(str(CLASSIFIED_POSTS), index=False)
    print(f"Classified posts saved to {CLASSIFIED_POSTS}")

    # Print summary for question posts only
    question_posts_df = classified_df[classified_df['type'] == 'question']

    print("\n=== Classification Summary (Questions Only) ===")
    print(f"Total questions: {len(question_posts_df)}")
    print(
        f"Questions with valid topic: {question_posts_df['topic'].notna().sum()}")
    print(
        f"Questions with no topic: {question_posts_df['topic'].isna().sum()}")
    print("\nTopic distribution (Questions Only):")
    print(question_posts_df['topic'].value_counts())


def main_classify_subtopics(model_path: Path, main_topic: str):
    """Classify posts within a specific main topic into subtopics.

    Uses the pre-classified posts (which must already contain normalized text)
    and applies the LDA model to only those posts whose `topic` equals
    `main_topic`. The inferred subtopic is written into the `subtopic` column.

    Args:
        model_path: Path to the directory containing the LDA model files.
        main_topic: The main topic to classify subtopics for.
    """
    # Load LDA model
    model_lda_path = model_path / TRAINED_LDA
    model_dct_path = model_path / TRAINED_DCT
    lda_config_path = model_path / 'topic_inference.json'

    if not model_lda_path.exists():
        raise FileNotFoundError(
            f"Trained LDA model not found at {model_lda_path}")

    if not model_dct_path.exists():
        raise FileNotFoundError(
            f"Trained dictionary not found at {model_dct_path}")

    print(f"Loading trained LDA model from {model_lda_path}")
    model = LdaModel.load(str(model_lda_path))
    print(f"Model loaded. Number of topics: {model.num_topics}")

    print(f"Loading topic names from {lda_config_path}")
    topic_mapping = load_topic_mapping(Path(lda_config_path))
    print(f"Loaded {len(topic_mapping)} topic names")

    # Load pre-classified posts (must contain normalized text already)
    if not Path(CLASSIFIED_POSTS).exists():
        raise FileNotFoundError(
            f"Classified posts not found at {CLASSIFIED_POSTS}")

    print(f"Loading classified posts from {CLASSIFIED_POSTS}")
    classified_df = pd.read_csv(str(CLASSIFIED_POSTS))
    print(f"Loaded {len(classified_df)} posts")

    # Ensure normalized text column exists in classified_df
    if 'normalized_text' not in classified_df.columns and 'normalized' in classified_df.columns:
        classified_df = classified_df.rename(
            columns={'normalized': 'normalized_text'})

    if 'normalized_text' not in classified_df.columns:
        raise ValueError(
            "Classified posts do not contain 'normalized_text' or 'normalized' column. Run normalization first.")

    # Classify posts in main_topic to subtopics (only process rows where topic == main_topic)
    print(f"Classifying posts in topic '{main_topic}' to subtopics...")
    subtopic_df = classify_posts_subtopic(
        model, classified_df, topic_mapping, main_topic)

    # Save with subtopic assignments
    Path(CLASSIFIED_POSTS).parent.mkdir(parents=True, exist_ok=True)
    subtopic_df.to_csv(str(CLASSIFIED_POSTS), index=False)
    print(f"Classified posts with subtopics saved to {CLASSIFIED_POSTS}")

    # Print summary for posts in main_topic only
    main_topic_mask = subtopic_df['topic'] == main_topic
    main_topic_posts = subtopic_df[main_topic_mask & (
        subtopic_df['type'] == 'question')]

    print(
        f"\n=== Subtopic Classification Summary (Main Topic: '{main_topic}') ===")
    print(f"Total questions in main topic: {len(main_topic_posts)}")
    print(
        f"Questions with valid subtopic: {main_topic_posts['subtopic'].notna().sum()}")
    print(
        f"Questions with no subtopic: {main_topic_posts['subtopic'].isna().sum()}")
    print("\\nSubtopic distribution:")
    print(main_topic_posts['subtopic'].value_counts())


if __name__ == '__main__':
    # main_classify_main_topics(MODELS / 'main')

    kd = pd.read_json(
        Path(MODELS / 'main' / 'trained_lda.meta.json'), orient='index').T
    ti = pd.read_json(Path(MODELS / 'main' / 'topic_inference.json'))

    k = kd['num_topics'].item()
    for c in range(int(k)):
        topic = ti.loc[c]['topics']['topic_name']
        main_classify_subtopics(MODELS / f't{c}', main_topic=topic)
        break
