import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openpyxl.worksheet.datavalidation import DataValidation
from pathlib import Path
import pandas as pd
from paths import *
import numpy as np
from math import ceil
import scipy.stats as st


def calc_sample_size(population, error_margin=0.05, confidence=0.95, p=0.5):
    """Cochran + Finite Population Correction"""
    Z = st.norm.ppf((1 + confidence) / 2)
    
    numerator = population * (Z**2) * p * (1 - p)
    denominator = (population - 1) * (error_margin**2) + (Z**2) * p * (1 - p)
    n = numerator / denominator

    return ceil(n)


def neyman_allocation(n, Nh_list, Sh_list):
    Nh = np.array(Nh_list)
    Sh = np.array(Sh_list)
    weights = Nh * Sh
    nh = n * (weights / weights.sum())
    return nh


def generate_stratum_table(classfication_path: str = CLASSIFIED_POSTS) -> None:
    df = pd.read_csv(classfication_path)
    qdf = df[df['type'] == 'question'].copy()
    grouped = qdf.groupby('topic')
    Nh = grouped.size()
    Sh = grouped['topic_perc_contrib'].std()
    N = len(qdf)
    
    z = 1.96  # nível de confiança 95%
    p = 0.5   # proporção estimada
    e = 0.05  # margem de erro
    n0 = (z**2 * p * (1 - p)) / (e**2)

    print(f"População total (N): {N}")
    print(f"Tamanho da amostra inicial (n₀): {n0}")
    
    n_fpc_float = n0 / (1 + (n0 - 1) / N)
    n_target = int(np.ceil(n_fpc_float)) 

    print(f"Tamanho da amostra ajustado FPC (n_alvo): {n_target}")
    
    # 2. ALOCAÇÃO DE NEYMAN 
    nh = neyman_allocation(
        n=n_fpc_float,
        Nh_list=Nh.values,
        Sh_list=Sh.values
    )
    print(f"Alocação de Neyman (floats): {nh}")
    
    # 3. ARREDONDAMENTO INICIAL
    nh_rounded = np.ceil(nh).astype(int)
    total_allocated = nh_rounded.sum()
    
    print(f"Total alocado após arredondamento inicial: {total_allocated}")
    print(nh_rounded)
    
    # 4. PROCESSO DE AJUSTE DE EXCESSO
    
    excess = total_allocated - n_target
    
    if excess > 0:
        print(f"Detectado excesso de {excess} unidade(s). Iniciando ajuste.")
        
        sobra = nh_rounded - nh
        indices_a_ajustar = np.argsort(sobra)[0:excess]
        
        nh_rounded[indices_a_ajustar] -= 1
        
        total_allocated = nh_rounded.sum()
        print(f"Ajuste concluído. Novo total alocado: {total_allocated}")

    print(nh_rounded)
    table = pd.DataFrame({
        'topic': Nh.index,
        'stratum_size (Nh)': Nh.values,
        'within_sd (Sh)': Sh.values,
        'allocated_nh': nh_rounded
    })
    table = table.sort_values('topic').reset_index(drop=True)
    table.to_csv(STRATUM_TABLE, index=False)


    """Read `STRATUM_TABLE`, sample `allocated_nh` questions per topic from `CLASSIFIED_POSTS`,
    and save the resulting rows to `VALIDATION_SAMPLE`.

    Samples are drawn without replacement per topic. If `allocated_nh` is larger than the
    number of available questions for a topic, all available questions are returned for
    that topic.
    
    Adds subtopics information from CLASSIFIED_POSTS.
    Outputs columns: id, site, topic, subtopics, link, topic_validation, subtopic_validation, technologies
    """
    stratum_df = pd.read_csv(STRATUM_TABLE)
    if 'topic' not in stratum_df.columns or 'allocated_nh' not in stratum_df.columns:
        raise ValueError(
            "STRATUM_TABLE must contain 'topic' and 'allocated_nh' columns")

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

    out_path = Path(VALIDATION_SAMPLE)
    if out_path.suffix.lower() != '.xlsx':
        out_path = out_path.with_suffix('.xlsx')

    def make_link(row):
        qid = row.get('question_id')
        site_alias = row.get('site_alias')
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
        out_df = pd.DataFrame(
            columns=['id', 'site', 'topic', 'subtopics', 'link', 
                    'topic_validation', 'subtopic_validation', 'technologies'])
    else:
        if 'id' not in result.columns and 'question_id' in result.columns:
            result = result.rename(columns={'question_id': 'id'})

        out_df = pd.DataFrame()
        out_df['id'] = result['question_id'] if 'question_id' in result.columns else pd.NA
        out_df['site'] = result['site_alias']
        out_df['topic'] = result['topic'] if 'topic' in result.columns else pd.NA
        
        sub_col = next(
            (c for c in result.columns if 'subtopic' in c.lower()), None)
        if sub_col:
            out_df['subtopics'] = result[sub_col]
        else:
            out_df['subtopics'] = pd.NA
            
        out_df['link'] = result.apply(make_link, axis=1)
        
        out_df['topic_validation'] = None
        out_df['subtopic_validation'] = None
        out_df['technologies'] = None

        out_df = out_df[['id', 'site', 'topic', 'subtopics', 'link', 
                        'topic_validation', 'subtopic_validation', 'technologies']]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            out_df.to_excel(writer, index=False,
                            sheet_name='validation_sample')

    except Exception as e:
        print(f"Failed to write with openpyxl, error: {e}")
        out_df.to_excel(out_path, index=False, sheet_name='validation_sample')

    return out_df


def validation_sample():
    """
    Deterministic PPS-style selection:
    For each topic (stratum), selects the 'allocated_nh' documents 
    with the highest `topic_perc_contrib` values (measure of size).

    This removes randomness entirely and ensures reproducibility,
    while preserving the principle that documents with higher semantic
    contribution to the topic are more likely to be included (now guaranteed).
    """

    stratum_df = pd.read_csv(STRATUM_TABLE)
    if 'topic' not in stratum_df.columns or 'allocated_nh' not in stratum_df.columns:
        raise ValueError(
            "STRATUM_TABLE must contain 'topic' and 'allocated_nh' columns"
        )

    classified_df = pd.read_csv(CLASSIFIED_POSTS)

    # only questions
    questions_df = classified_df[classified_df['type'] == 'question'].copy()

    # must exist
    if 'topic_perc_contrib' not in questions_df.columns:
        raise ValueError(
            "CLASSIFIED_POSTS must contain 'topic_perc_contrib' column"
        )

    # remove missing and non-positive size measure
    questions_df = questions_df[
        questions_df['topic_perc_contrib'].notna()
        & (questions_df['topic_perc_contrib'] > 0)
    ].copy()

    samples = []

    for _, row in stratum_df.iterrows():
        topic = row['topic']

        try:
            nh = int(row['allocated_nh'])
        except Exception:
            nh = 0

        if nh <= 0:
            continue

        candidates = questions_df[questions_df['topic'] == topic].copy()

        if candidates.empty:
            continue

        # sort by measure of size descending (deterministic PPS)
        candidates = candidates.sort_values(
            by='topic_perc_contrib',
            ascending=False
        )

        # if fewer than nh exist → take all
        sampled = candidates.head(nh)

        samples.append(sampled)

    if samples:
        result = pd.concat(samples, ignore_index=True)
    else:
        result = pd.DataFrame(columns=classified_df.columns)

    # ensure no duplicates but keep order
    result = result.drop_duplicates(subset=['question_id'])

    out_path = Path(VALIDATION_SAMPLE).with_suffix('.xlsx')

    def make_link(row):
        qid = row.get('question_id')
        site_alias = row.get('site_alias')

        if pd.isna(qid):
            return ''

        qid = str(int(qid)) if not pd.isna(qid) else ''

        if str(site_alias) == 'stackoverflow':
            domain = 'stackoverflow.com'
        else:
            domain = f"{site_alias}.stackexchange.com"

        return f"https://{domain}/questions/{qid}"

    # build final dataframe
    if result.empty:
        out_df = pd.DataFrame(
            columns=[
                'id', 'site', 'topic', 'subtopics', 'link',
                'topic_validation', 'subtopic_validation', 'technologies'
            ]
        )
    else:
        if 'id' not in result.columns and 'question_id' in result.columns:
            result = result.rename(columns={'question_id': 'id'})

        out_df = pd.DataFrame()
        out_df['id'] = result['id']
        out_df['site'] = result['site_alias']
        out_df['topic'] = result['topic']

        sub_col = next((c for c in result.columns if 'subtopic' in c.lower()), None)
        out_df['subtopics'] = result[sub_col] if sub_col else pd.NA

        out_df['link'] = result.apply(make_link, axis=1)

        out_df['topic_validation'] = None
        out_df['subtopic_validation'] = None
        out_df['technologies'] = None

    out_df = out_df[
        ['id', 'site', 'topic', 'subtopics', 'link', 'topic1', 'topic2',
         'topic_validation', 'subtopic1', 'subtopic2', 'subtopic_validation', 'technologies']
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        out_df.to_excel(writer, index=False, sheet_name='validation_sample')

    return out_df


if __name__ == '__main__':
    generate_stratum_table()