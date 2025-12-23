import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openpyxl.worksheet.datavalidation import DataValidation
from pathlib import Path
import pandas as pd
from paths import *
from utils_global import calc_sample_size, neyman_allocation
import numpy as np
from math import ceil


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
    
    # 1. CÁLCULO DE 'n' COM FPC
    n_fpc_float = n0 / (1 + (n0 - 1) / N) # Valor float sem arredondamento
    
    # O tamanho da amostra final desejado é o arredondamento superior deste float
    n_target = int(np.ceil(n_fpc_float)) 

    print(f"Tamanho da amostra ajustado FPC (n_alvo): {n_target}")
    
    # 2. ALOCAÇÃO DE NEYMAN (nh é um array de floats)
    nh = neyman_allocation(
        n=n_fpc_float, # Usa o valor float para a proporção correta
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
    # O objetivo é garantir que total_allocated <= n_target (idealmente, = n_target)
    
    excess = total_allocated - n_target
    
    if excess > 0:
        print(f"⚠️ Detectado excesso de {excess} unidade(s). Iniciando ajuste.")
        
        # 4a. Calcula a "sobra" (a parte decimal que causou o arredondamento)
        # Queremos ajustar (subtrair 1) os estratos onde a sobra é menor.
        sobra = nh_rounded - nh # Quanto o arredondamento adicionou (Ex: 11 - 10.9 = 0.1)
        
        # 4b. Encontra os índices dos 'excess' estratos com a menor sobra (menor benefício do arredondamento)
        # argsort(sobra) ordena os índices pela menor sobra (crescente)
        indices_a_ajustar = np.argsort(sobra)[0:excess]
        
        # 4c. Subtrai 1 unidade de cada um desses estratos para corrigir o excesso
        nh_rounded[indices_a_ajustar] -= 1
        
        # Atualiza o total após o ajuste
        total_allocated = nh_rounded.sum()
        print(f"✅ Ajuste concluído. Novo total alocado: {total_allocated}")

    print(nh_rounded)
    # 5. MONTAGEM DA TABELA
    table = pd.DataFrame({
        'topic': Nh.index,
        'stratum_size (Nh)': Nh.values,
        'within_sd (Sh)': Sh.values,
        'allocated_nh': nh_rounded
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
            columns=['id', 'site', 'topic', 'link', 'is_valid'])
    else:
        # Ensure id and topic exist in result; fall back to 'question_id' if needed
        if 'id' not in result.columns and 'question_id' in result.columns:
            result = result.rename(columns={'question_id': 'id'})

        out_df = pd.DataFrame()
        out_df['id'] = result['question_id'] if 'id' in result.columns else pd.NA
        out_df['site'] = result['site_alias']

        out_df['topic'] = result['topic'] if 'topic' in result.columns else pd.NA
        out_df['link'] = result.apply(make_link, axis=1)
        out_df['is_valid'] = None  # Placeholder for dropdown

        # Ensure correct column order
        out_df = out_df[['id', 'site', 'topic', 'link', 'is_valid']]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Write to Excel
    try:
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            out_df.to_excel(writer, index=False,
                            sheet_name='validation_sample')

            # Add data validation for 'is_valid' column
            workbook = writer.book
            worksheet = writer.sheets['validation_sample']
            dv = DataValidation(
                type="list", formula1='"True,False"', allow_blank=True)
            worksheet.add_data_validation(dv)
            # Apply validation to all cells in the 'is_valid' column (column E)
            # from the second row to the last row of data.
            if not out_df.empty:
                dv.add(f'E2:E{len(out_df)+1}')

    except Exception as e:
        print(f"Failed to write with openpyxl and data validation, error: {e}")
        # Fallback: try default engine without data validation
        out_df.to_excel(out_path, index=False, sheet_name='validation_sample')

    return out_df


def regenarete_validation_sample(validation_path: str = VALIDATION_SAMPLE,
                                 classified_path: str = CLASSIFIED_POSTS,
                                 stratum_path: str = STRATUM_TABLE,
                                 out_filename: str = 'new_validation_sample.xlsx') -> pd.DataFrame:
    """Read `validation_path` Excel, regenerate a new validation sample file
    with columns `new_topic` and `old_topic`, ensuring the counts per topic
    match `stratum_path` (`allocated_nh`). The function updates rows in-place
    (no new rows are created). If substitutions are needed to meet the
    allocation, existing rows are replaced with candidates from
    `classified_path`; replaced rows have `old_topic` and `is_valid*` left blank.
    Returns the resulting DataFrame and writes it to `LDA_DIR / out_filename`.
    """

    # Read existing validation sheet
    try:
        vs_df = pd.read_excel(validation_path, sheet_name='validation_sample')
    except Exception:
        vs_df = pd.read_excel(validation_path)

    # Detect id column and is_valid columns
    id_col = 'id' if 'id' in vs_df.columns else (
        'question_id' if 'question_id' in vs_df.columns else None)
    if id_col is None:
        raise ValueError(
            'Validation sheet must contain an `id` or `question_id` column')

    is_valid_cols = [c for c in vs_df.columns if str(
        c).lower().startswith('is_valid')]

    # Capture old topic column if present
    old_topic_col_in_sheet = 'topic' if 'topic' in vs_df.columns else None
    old_topics = vs_df[old_topic_col_in_sheet].astype(
        object) if old_topic_col_in_sheet else pd.Series([pd.NA]*len(vs_df))

    # Read classified posts and stratum table
    classified = pd.read_csv(classified_path)
    questions = classified[classified['type'] == 'question'].copy()

    # Normalize id types for mapping
    questions['question_id_str'] = questions['question_id'].apply(
        lambda x: str(int(x)) if pd.notna(x) else '')
    id_to_topic = {str(int(r['question_id'])): r.get(
        'topic') for _, r in questions.iterrows() if pd.notna(r.get('question_id'))}
    id_to_site = {str(int(r['question_id'])): r.get('site_alias')
                  for _, r in questions.iterrows() if pd.notna(r.get('question_id'))}

    stratum = pd.read_csv(stratum_path)
    # target counts per topic
    need = {row['topic']: int(row.get('allocated_nh', 0))
            for _, row in stratum.iterrows()}

    # Map existing rows to their mapped new topic (from classified)
    def map_id_to_topic(val):
        try:
            k = str(int(val))
        except Exception:
            k = str(val)
        return id_to_topic.get(k)

    vs_df['_mapped_new_topic'] = vs_df[id_col].apply(map_id_to_topic)

    # Prepare candidate pools per topic (ids as strings)
    candidates_by_topic = {}
    for t, g in questions.groupby('topic'):
        ids = [str(int(x)) for x in g['question_id'].values if pd.notna(x)]
        candidates_by_topic[t] = ids

    # Track which indices we'll keep (prefer existing rows that already map to the topic)
    kept = set()
    assigned_new_topic = [None] * len(vs_df)

    # First pass: keep existing mapped rows up to need
    for topic, cnt in need.items():
        if cnt <= 0:
            continue
        # indices where mapped topic equals this topic
        matching_idx = [i for i, v in enumerate(
            vs_df['_mapped_new_topic'].tolist()) if v == topic]
        take = matching_idx[:cnt]
        for i in take:
            kept.add(i)
            assigned_new_topic[i] = topic
        need[topic] = max(0, cnt - len(take))

    # Build set of ids already in kept rows to avoid duplicates
    kept_ids = set()
    for i in kept:
        try:
            kept_ids.add(str(int(vs_df.at[i, id_col])))
        except Exception:
            kept_ids.add(str(vs_df.at[i, id_col]))

    # Second pass: fill remaining needs using candidate pools, replacing non-kept rows
    replaceable_indices = [i for i in range(len(vs_df)) if i not in kept]
    rep_ptr = 0

    for topic, cnt in need.items():
        if cnt <= 0:
            continue
        candidates = list(candidates_by_topic.get(topic, []))
        # remove candidates that are already present in the sheet (either kept or elsewhere)
        existing_sheet_ids = set()
        for v in vs_df[id_col].fillna('').tolist():
            try:
                existing_sheet_ids.add(str(int(v)))
            except Exception:
                existing_sheet_ids.add(str(v))
        candidates = [c for c in candidates if c not in existing_sheet_ids]

        for _ in range(cnt):
            if rep_ptr >= len(replaceable_indices):
                # No more rows to replace; stop trying
                break
            if not candidates:
                break
            pick_id = candidates.pop(0)
            idx = replaceable_indices[rep_ptr]
            rep_ptr += 1
            assigned_new_topic[idx] = topic
            # set new id/site in DataFrame for replaced row
            vs_df.at[idx, id_col] = int(
                pick_id) if pick_id.isdigit() else pick_id
            vs_df.at[idx, 'site'] = id_to_site.get(
                pick_id, vs_df.at[idx, 'site'] if 'site' in vs_df.columns else pd.NA)
            kept_ids.add(pick_id)
            # Mark as replaced (not in kept)

    # Build output DataFrame keeping the same number of rows
    out = pd.DataFrame(index=vs_df.index)

    # old_topic is the topic value that was in the sheet
    out['old_topic'] = old_topics.values

    # new_topic is assigned_new_topic if available, otherwise mapped value
    for i in range(len(vs_df)):
        if assigned_new_topic[i] is None:
            assigned_new_topic[i] = vs_df.at[i, '_mapped_new_topic']

    out['new_topic'] = assigned_new_topic

    # id and site and link
    out['id'] = vs_df[id_col]
    out['site'] = vs_df['site'] if 'site' in vs_df.columns else out['id'].apply(
        lambda x: pd.NA)

    def make_link_row(val, site_alias):
        if pd.isna(val):
            return ''
        try:
            qid_str = str(int(val))
        except Exception:
            qid_str = str(val)
        if str(site_alias) == 'stackoverflow':
            domain = 'stackoverflow.com'
        elif pd.isna(site_alias) or site_alias == 'nan':
            domain = ''
        else:
            domain = f"{site_alias}.stackexchange.com"
        return f"https://{domain}/questions/{qid_str}" if domain else ''

    out['link'] = [make_link_row(i, s) for i, s in zip(
        out['id'].tolist(), out['site'].tolist())]

    # Preserve is_valid columns only for kept rows; cleared for replaced rows
    for col in is_valid_cols:
        if col in vs_df.columns:
            out[col] = vs_df[col].where(vs_df.index.isin(kept), other=pd.NA)

    # Ensure no new rows have been created; write to Excel
    out_path = Path(VALIDATION_SAMPLE).parent / out_filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            out.to_excel(writer, index=False, sheet_name='validation_sample')
    except Exception as e:
        # fallback
        out.to_excel(out_path, index=False, sheet_name='validation_sample')

    # Clean temporary column
    if '_mapped_new_topic' in vs_df.columns:
        vs_df.drop(columns=['_mapped_new_topic'], inplace=True)

    return out


def add_subtopics(validation_path: str = VALIDATION_SAMPLE,
                  classified_path: str = CLASSIFIED_POSTS) -> pd.DataFrame:
    """Add a `subtopics` column to the validation sample file based on
    `classified_path`. Matching is done by `id` (or `question_id`) and `site`.
    The function writes the updated sheet back to `validation_path` and
    returns the updated DataFrame.
    """

    # Read validation sheet
    try:
        vs_df = pd.read_excel(validation_path, sheet_name='validation_sample')
    except Exception:
        vs_df = pd.read_excel(validation_path)

    # Identify id and site columns in validation sheet
    id_col = 'id' if 'id' in vs_df.columns else (
        'question_id' if 'question_id' in vs_df.columns else None)
    if id_col is None:
        raise ValueError(
            'Validation sheet must contain an `id` or `question_id` column')

    site_col_vs = 'site' if 'site' in vs_df.columns else (
        'site_alias' if 'site_alias' in vs_df.columns else None)

    # Read classified posts
    classified = pd.read_csv(classified_path)

    # Find a column that looks like a subtopic column
    sub_col = next(
        (c for c in classified.columns if 'subtopic' in c.lower()), None)
    if sub_col is None:
        # No subtopic info available: add empty column and write back
        vs_df['subtopics'] = pd.NA
        out_path = Path(validation_path)
        if out_path.suffix.lower() != '.xlsx':
            out_path = out_path.with_suffix('.xlsx')
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            vs_df.to_excel(writer, index=False, sheet_name='validation_sample')
        return vs_df

    # Normalize classified id and site columns
    if 'question_id' not in classified.columns and 'id' in classified.columns:
        classified = classified.rename(columns={'id': 'question_id'})

    site_col_class = 'site_alias' if 'site_alias' in classified.columns else (
        'site' if 'site' in classified.columns else None)

    def id_to_str(x):
        if pd.isna(x):
            return ''
        try:
            return str(int(x))
        except Exception:
            return str(x)

    classified['_qid_str'] = classified['question_id'].apply(
        id_to_str) if 'question_id' in classified.columns else pd.Series(['']*len(classified))
    if site_col_class:
        classified['_site_str'] = classified[site_col_class].astype(str)
    else:
        classified['_site_str'] = ''

    # Build mapping (qid_str, site_str) -> subtopic
    mapping = {}
    for _, r in classified.iterrows():
        key = (r.get('_qid_str', ''), str(r.get('_site_str', '')))
        if pd.notna(r.get(sub_col)):
            mapping[key] = r.get(sub_col)

    # Also build fallback mapping by id only
    id_only_map = {k[0]: v for k, v in mapping.items() if k[0]}

    # Populate subtopics column
    subs = []
    for _, row in vs_df.iterrows():
        qid = row.get(id_col)
        qid_s = id_to_str(qid)
        site_vs = row.get(site_col_vs) if site_col_vs else ''
        site_vs_s = '' if pd.isna(site_vs) else str(site_vs)
        val = mapping.get((qid_s, site_vs_s))
        if val is None:
            val = id_only_map.get(qid_s)
        subs.append(val if pd.notna(val) else pd.NA)

    vs_df['subtopics'] = subs

    # Write back to the same validation file (xlsx preferred)
    out_path = Path(validation_path)
    if out_path.suffix.lower() != '.xlsx':
        out_path = out_path.with_suffix('.xlsx')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        vs_df.to_excel(writer, index=False, sheet_name='validation_sample_sub')

    return vs_df


if __name__ == '__main__':
    generate_stratum_table()
    validation_sample()
    add_subtopics()