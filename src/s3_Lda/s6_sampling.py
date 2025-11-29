import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_global import calc_sample_size, neyman_allocation
from paths import *
import pandas as pd


def generate_stratum_table(df=CLASSIFIED_POSTS):

    qdf = df[df['type'] == 'question'].copy()
    grouped = qdf.groupby('topic')

    Nh = grouped.size()
    Sh = grouped['topic_perc_contrib'].std()

    N = len(qdf)
    n = calc_sample_size(N)

    nh = neyman_allocation(
        n=n,
        Nh_list=Nh.values,
        Sh_list=Sh.values
    )

    table = pd.DataFrame({
        'topic': Nh.index,
        'stratum_size (Nh)': Nh.values,
        'within_sd (Sh)': Sh.values,
        'allocated_nh': nh
    })

    table = table.sort_values('topic').reset_index(drop=True)

    output_path = f"{STRATUM_TABLE}/stratum_table.csv"
    table.to_csv(output_path, index=False)


if __name__ == '__main__':
    generate_stratum_table()
