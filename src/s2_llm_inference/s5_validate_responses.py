import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import *
import pandas as pd
import math
import pandas as pd
import scipy.stats as st
import numpy as np


def calc_sample_size(population, error_margin=0.05, confidence=0.95, p=0.5):
    """(Finite Population Correction - FPC)"""
    Z = st.norm.ppf((1 + confidence) / 2)
    
    numerator = population * (Z**2) * p * (1 - p)
    denominator = (population - 1) * (error_margin**2) + (Z**2) * p * (1 - p)
    n = numerator / denominator

    return math.ceil(n)


def generate_validation_xlsx(n_samples: int):
    """
    Reads 'n' samples from the PREPROCESSED_POSTS file and places them in an xlsx spreadsheet.

    The spreadsheet will have the following columns:
    - post_link: URL to the post.
    - has_misuse: Empty column for manual validation.
    - types: Empty column for manual validation.
    - question_id: The ID of the question.
    - site: The site alias.

    Args:
        n_samples: The number of samples to process.
    """
    posts_df = pd.read_csv(PREPROCESSED_POSTS, nrows=n_samples)

    validation_data = []

    for _, row in posts_df.iterrows():
        if row['type'] != 'question':
            continue
        question_id = row['question_id']
        site_alias = row['site_alias']

        if site_alias == 'stackoverflow':
            post_link = f"https://stackoverflow.com/questions/{question_id}"
        else:
            post_link = f"https://{site_alias}.stackexchange.com/questions/{question_id}"

        validation_data.append({
            'question_id': question_id,
            'site': site_alias,
            'post_link': post_link,
            'c1 d': '',
            'c1 t': '',
            'c2 d': '',
            'c2 t': '',
            'c3 d': '',
            'c3 t': '',
            'c4 d': '',
            'c4 t': '',
            'c5 d': '',
            'c5 t': '',
            'c6 d': '',
            'c6 t': '',
            'c7 d': '',
            'c7 t': '',
        })

    validation_df = pd.DataFrame(validation_data)

    validation_df.to_excel(VALIDATION_SHEET, index=False)
    print(f"Validation sheet saved to {VALIDATION_SHEET}")


if __name__ == '__main__':
    generate_validation_xlsx(n_samples=1000)
