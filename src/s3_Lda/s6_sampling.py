import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_global import calc_sample_size, neyman_allocation
from paths import *
import pandas as pd
from pathlib import Path


def generate_stratum_table(classfication_path: str = CLASSIFIED_POSTS) -> None:

    df = pd.read_csv(classfication_path)

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

    table.to_csv(STRATUM_TABLE, index=False)


def validation_sample():
    """Read `STRATUM_TABLE`, sample `allocated_nh` questions per topic from `CLASSIFIED_POSTS`,
    and save the resulting rows to `VALIDATION_SAMPLE`.

    Samples are drawn without replacement per topic. If `allocated_nh` is larger than the
    number of available questions for a topic, all available questions are returned for
    that topic.
    """
    # Read stratum table
    stratum_df = pd.read_csv(STRATUM_TABLE)
    if 'topic' not in stratum_df.columns or 'allocated_nh' not in stratum_df.columns:
        raise ValueError(
            "STRATUM_TABLE must contain 'topic' and 'allocated_nh' columns")

    # Load classified posts and filter questions
    classified_df = pd.read_csv(CLASSIFIED_POSTS)
    questions_df = classified_df[classified_df['type'] == 'question'].copy()

    samples = []
    for _, row in stratum_df.iterrows():
        topic = row['topic']
        try:
            nh = int(row['allocated_nh'])
        except Exception:
            nh = 0
        if nh <= 0:
            continue

        candidates = questions_df[questions_df['topic'] == topic]
        if candidates.empty:
            continue

        if nh >= len(candidates):
            sampled = candidates.copy()
        else:
            sampled = candidates.sample(n=nh, replace=False)

        samples.append(sampled)

    if samples:
        result = pd.concat(
            samples, ignore_index=True).drop_duplicates().reset_index(drop=True)
    else:
        result = pd.DataFrame(columns=classified_df.columns)

    # Prepare output path: prefer .xlsx
    out_path = Path(VALIDATION_SAMPLE)
    if out_path.suffix.lower() != '.xlsx':
        out_path = out_path.with_suffix('.xlsx')

    # Build sheet with required columns: question_id, link, topic
    # Determine site column name if present
    site_col = None
    if 'site' in result.columns:
        site_col = 'site'
    elif 'site_alias' in result.columns:
        site_col = 'site_alias'

    def make_link(row):
        qid = row.get('question_id') if 'question_id' in row else row.get('id')
        site_alias = row.get(
            site_col) if site_col is not None else 'stackoverflow'
        if pd.isna(qid):
            return ''
        try:
            qid_str = str(int(qid))
        except Exception:
            qid_str = str(qid)
        if str(site_alias) == 'stackoverflow':
            domain = 'stackoverflow.com'
        else:
            domain = f"{site_alias}.stackexchange.com"
        return f"https://{domain}/questions/{qid_str}"

    if result.empty:
        out_df = pd.DataFrame(columns=['question_id', 'link', 'topic'])
    else:
        # Ensure question_id and topic exist in result; fall back to 'id' if needed
        if 'question_id' not in result.columns and 'id' in result.columns:
            result = result.rename(columns={'id': 'question_id'})

        out_df = pd.DataFrame()
        out_df['question_id'] = result['question_id'] if 'question_id' in result.columns else pd.NA
        out_df['topic'] = result['topic'] if 'topic' in result.columns else pd.NA
        out_df['link'] = result.apply(make_link, axis=1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Write to Excel
    try:
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            out_df.to_excel(writer, index=False,
                            sheet_name='validation_sample')
    except Exception:
        # Fallback: try default engine
        out_df.to_excel(out_path, index=False, sheet_name='validation_sample')

    return out_df


if __name__ == '__main__':
    generate_stratum_table()
    validation_sample()
