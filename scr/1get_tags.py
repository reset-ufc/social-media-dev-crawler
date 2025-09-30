import os
import pandas as pd
import re
import ast

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


def make_releated_tags():
    if not os.path.exists(RELEATED_TAGS):
        df_coarse = pd.read_csv(COARSE_POST_PATH)

        df_coarse['Tags'] = df_coarse['Tags'].apply(ast.literal_eval)
        
        explode_tags = df_coarse['Tags'].explode()
        releated_tags = explode_tags.value_counts().to_dict()
        
        if QUESTION_TAG in releated_tags.keys():
            releated_tags.pop(QUESTION_TAG)
        
        rt = pd.DataFrame.from_dict(releated_tags, orient='index', columns=['ocorr'])
        rt = rt.reset_index().rename(columns={'index': 'tag'})
        
        rt.to_json(RELEATED_TAGS, orient='records', lines=True)
    

def find_representative_tags():
    releated_tags = pd.read_json(RELEATED_TAGS, lines=True)


def make_df_fine():
    ...


make_df_coarse()
make_releated_tags()

pd.read_json(RELEATED_TAGS, lines=True)