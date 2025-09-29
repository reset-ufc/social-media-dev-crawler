import os
import pandas as pd
import re

QUESTION_TAG = "encryption"
BASE_DIR = "./dump"


def preprocess_posts(df):
    """ 
    Adequa a coluna Tags para busca
    """
    df.dropna(subset=['Tags'], inplace=True)
    df['Tags'] = df['Tags'].str.strip('<>').str.split('><')
    return df


def get_main_tag_posts():
    posts_path = os.path.join(BASE_DIR, "Posts.xml")
    if not os.path.exists(posts_path):
        print(f"⚠ Posts.xml não encontrado em: {posts_path}")
        return
    df = preprocess_posts(
        pd.read_xml(posts_path)
    )
    df_filtred = df[
        df['Tags'].apply(lambda l: QUESTION_TAG in l)
    ]
    return df_filtred


def search_releated_tags(df_filtred):
    ...


print(get_main_tag_posts().head())
