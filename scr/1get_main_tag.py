import os
import pandas as pd
import re

QUESTION_TAG = "encryption"
BASE_DIR = "./dump"


def preprocess_posts(df):
    df.dropna(subset=['Tags'], inplace=True)

    # Adequa as tags para busca
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
    print(df['Tags'].head())


get_main_tag_posts()