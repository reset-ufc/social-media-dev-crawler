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
        print(
            f"Warning: Could not find topic ID or name columns in {topic_inference_path}. Topic names will be unknown.")
        return {}

    topic_mapping = topics_df.set_index(id_col)[name_col].to_dict()

    return topic_mapping


def _classify_post_groups(model: LdaModel, posts_df: pd.DataFrame, topic_mapping: dict, topic_col_name: str, perc_col_name: str, filter_col: str = None, filter_val: str = None) -> pd.DataFrame:
    """Internal helper to classify post groups, modifying the DataFrame."""
    df_to_process = posts_df
    if filter_col and filter_val:
        mask = posts_df[filter_col] == filter_val
        df_to_process = posts_df[mask]

    grouped = df_to_process.groupby(['site', 'question_id'])
    processed_count = 0

    for _, group in grouped:
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
        topic_name = topic_mapping.get(
            most_probable_topic_id, most_probable_topic_id)

        question_post_index = group[group['type'] == 'question'].index
        if not question_post_index.empty:
            posts_df.loc[question_post_index, topic_col_name] = topic_name
            posts_df.loc[question_post_index,
                         perc_col_name] = most_probable_topic_percentage
            processed_count += 1

    if filter_val:
        print(f"  Processed {processed_count} questions for topic '{filter_val}'")

    return posts_df


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

    return _classify_post_groups(
        model=model,
        posts_df=result_df,
        topic_mapping=topic_mapping,
        topic_col_name='topic',
        perc_col_name='topic_perc_contrib'
    )


def classify_posts_subtopic(model: LdaModel, posts_df: pd.DataFrame, topic_mapping: dict, main_topic: str) -> pd.DataFrame:
    """
    Classifies post groups within a specific main topic to subtopics.
    Only processes posts where 'topic' == main_topic.
    Adds 'subtopic' column with the inferred subtopic names.
    Adds 'subtopic_perc_contrib' column with the subtopic contribution percentage.
    
    IMPORTANTE: Esta função NÃO inicializa as colunas, apenas atualiza os valores
    para o main_topic especificado.
    """
    result_df = posts_df.copy()
    
    return _classify_post_groups(
        model=model,
        posts_df=result_df,
        topic_mapping=topic_mapping,
        topic_col_name='subtopic',
        perc_col_name='subtopic_perc_contrib',
        filter_col='topic',
        filter_val=main_topic
    )


def classify_main_topics(model_path):
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

    print(f"Loading topic names from {model_path / LDA_TOPIC_INFERENCE}")
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


def classify_all_subtopics(model_path):
    """Classify all main topics into subtopics in a single pass.
    
    Esta função carrega o arquivo UMA VEZ, processa todos os tópicos,
    e salva UMA VEZ no final para evitar sobrescrever.
    """
    # Load main topic configuration
    kd = pd.read_json(
        Path(model_path / 'trained_lda.meta.json'), orient='index').T
    ti = pd.read_json(Path(model_path / LDA_TOPIC_INFERENCE))
    
    k = int(kd['num_topics'].item())
    print(f"Found {k} main topics to process")
    
    # Load classified posts ONCE
    if not Path(CLASSIFIED_POSTS).exists():
        raise FileNotFoundError(
            f"Classified posts not found at {CLASSIFIED_POSTS}")
    
    print(f"\nLoading classified posts from {CLASSIFIED_POSTS}")
    classified_df = pd.read_csv(str(CLASSIFIED_POSTS))
    print(f"Loaded {len(classified_df)} posts")
    
    # Initialize subtopic columns if they don't exist
    if 'subtopic' not in classified_df.columns:
        classified_df['subtopic'] = pd.NA
    if 'subtopic_perc_contrib' not in classified_df.columns:
        classified_df['subtopic_perc_contrib'] = pd.NA
    
    # Ensure normalized_text column exists
    if 'normalized_text' not in classified_df.columns and 'normalized' in classified_df.columns:
        classified_df = classified_df.rename(columns={'normalized': 'normalized_text'})
    
    if 'normalized_text' not in classified_df.columns:
        raise ValueError(
            "Classified posts do not contain 'normalized_text' or 'normalized' column.")
    
    # Process each main topic
    for c in range(k):
        topic_name = ti.loc[c]['topics']['topic_name']
        model_path = MODELS / f't{c}'
        
        print(f"\n[{c+1}/{k}] Processing topic: '{topic_name}'")
        
        # Check if model exists
        if not model_path.exists():
            print(f"  WARNING: Model path does not exist: {model_path}")
            continue
        
        lda_file = model_path / TRAINED_LDA
        dct_file = model_path / TRAINED_DCT
        inf_file = model_path / 'topic_inference.json'
        
        if not lda_file.exists() or not dct_file.exists():
            print(f"WARNING: Model files not found in {model_path}")
            continue
        
        print(f"  Loading model from {model_path}")
        model = LdaModel.load(str(lda_file))
        dictionary = Dictionary.load(str(dct_file))
        model.id2word = dictionary  # CRITICAL: Associate dictionary with model
        
        # Load topic mapping
        topic_mapping = load_topic_mapping(inf_file)
        print(f"  Loaded {len(topic_mapping)} subtopic names")
        
        # Classify subtopics for this main topic
        classified_df = classify_posts_subtopic(
            model, classified_df, topic_mapping, topic_name)
    
    print(f"\nSaving all results to {CLASSIFIED_POSTS}")
    classified_df.to_csv(str(CLASSIFIED_POSTS), index=False)
    
    question_posts = classified_df[classified_df['type'] == 'question']
    
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Total questions: {len(question_posts)}")
    print(f"Questions with topic: {question_posts['topic'].notna().sum()}")
    print(f"Questions with subtopic: {question_posts['subtopic'].notna().sum()}")
    
    print("\nSubtopic coverage by main topic:")
    for topic in question_posts['topic'].dropna().unique():
        topic_mask = question_posts['topic'] == topic
        total = topic_mask.sum()
        with_subtopic = (topic_mask & question_posts['subtopic'].notna()).sum()
        print(f"  {topic}: {with_subtopic}/{total} ({100*with_subtopic/total:.1f}%)")


if __name__ == '__main__':
    classify_main_topics(MODELS / 'main1')
    #classify_all_subtopics(MODELS / 'main1')