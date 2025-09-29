import os
import pandas as pd
import re

from config import *


def preprocess_posts(df):
    """ 
    Adequa a coluna Tags para busca
    """
    df.dropna(subset=['Tags'], inplace=True)
    df['Tags'] = df['Tags'].str.strip('<>').str.split('><')
    return df


def make_df_coarse():
    if not os.path.exists(DUMP_POST_PATH):
        print(f"⚠ Posts.xml não encontrado em: {DUMP_POST_PATH}")
        return
    if not os.path.exists(COARSE_POST_PATH):
        df = preprocess_posts(
            pd.read_xml(DUMP_POST_PATH)
        )
        df_coarse = df[
            df['Tags'].apply(lambda l: QUESTION_TAG in l)
        ]
        df_coarse.to_csv(COARSE_POST_PATH)


def search_releated_tags():
    df_coarse = pd.read_csv(COARSE_POST_PATH)

    explode_tags = df_coarse['Tags'].explode()
    releated_tags = explode_tags.unique().tolist()
    if QUESTION_TAG in releated_tags:
        releated_tags.remove(QUESTION_TAG)

    print(releated_tags)
    

make_df_coarse()
print(search_releated_tags())
