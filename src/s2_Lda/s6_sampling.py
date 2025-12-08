from openpyxl.worksheet.datavalidation import DataValidation
from pathlib import Path
import pandas as pd
from paths import *
from utils_global import calc_sample_size, neyman_allocation
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def regenerate_validation(output_path: str = None):
    """
    Regenerates the validation sample by updating topics for existing posts
    and enforcing stratum allocations by removing or adding posts to meet
    targets.

    - Updates `topic` for existing posts based on `CLASSIFIED_POSTS`.
    - Adds `old_topic` and `new_topic` columns to track changes.
    - Removes posts from over-represented topics.
    - Adds posts to under-represented topics. For these new posts, `is_valid_1`
      and `is_valid_2` (if they exist) are cleared.
    - Saves the updated sample to a new Excel file.
    """
    in_path = Path(VALIDATION_SAMPLE)
    if not in_path.exists():
        raise FileNotFoundError(f"Validation sample not found at {in_path}")

    if not Path(STRATUM_TABLE).exists():
        raise FileNotFoundError(f"Stratum table not found at {STRATUM_TABLE}")
    stratum_df = pd.read_csv(STRATUM_TABLE)
    allocation_target = dict(
        zip(stratum_df['topic'], stratum_df['allocated_nh']))

    df = pd.read_excel(in_path)
    updated = df.copy()

    # --- 1. Add new columns and update topics ---
    updated['old_topic'] = updated['topic'] if 'topic' in updated.columns else pd.NA
    updated['new_topic'] = updated['old_topic']

    if 'question_id' in updated.columns:
        id_col = 'question_id'
    else:
        id_col = 'id'

    updated[id_col] = updated[id_col].astype(
        str).str.split('.').str[0]

    classified = pd.read_csv(CLASSIFIED_POSTS, dtype={'question_id': str})
    classified['question_id'] = classified['question_id'].str.split('.').str[0]
    topic_mapping = dict(
        zip(classified['question_id'], classified.get('topic')))

    # Update new_topic based on the mapping
    updated['new_topic'] = updated[id_col].map(topic_mapping)
    # If a post is not in the new classified posts, keep its old topic
    updated['new_topic'].fillna(updated['old_topic'], inplace=True)
    updated['topic'] = updated['new_topic']

    # --- 2. Enforce stratum allocations ---
    topic_counts = updated['topic'].value_counts().to_dict()
    excess_per_topic = {t: topic_counts.get(
        t, 0) - a for t, a in allocation_target.items() if topic_counts.get(t, 0) > a}
    deficit_per_topic = {t: a - topic_counts.get(
        t, 0) for t, a in allocation_target.items() if topic_counts.get(t, 0) < a}

    # Remove excess posts
    indices_to_drop = []
    for topic, excess in excess_per_topic.items():
        indices = updated[updated['topic'] == topic].index
        indices_to_drop.extend(list(indices[:excess]))
    updated.drop(indices_to_drop, inplace=True)
    updated.reset_index(drop=True, inplace=True)

    # Add missing posts
    current_ids = set(updated[id_col])
    new_rows = []
    for topic, deficit in deficit_per_topic.items():
        candidates = classified[(classified['topic'] == topic) &
                                (classified['type'] == 'question') &
                                (~classified['question_id'].isin(current_ids))]
        sample_size = min(deficit, len(candidates))
        if sample_size > 0:
            sampled = candidates.sample(n=sample_size, replace=False)
            for _, row in sampled.iterrows():
                new_row = {
                    id_col: row['question_id'],
                    'site': row.get('site_alias', ''),
                    'topic': topic,
                    'old_topic': None,
                    'new_topic': topic,
                    'is_valid_1': None,
                    'is_valid_2': None,
                    'link': f"https://{row.get('site_alias', '')}.stackexchange.com/questions/{row['question_id']}"
                }
                new_rows.append(new_row)
            current_ids.update(sampled['question_id'].tolist())

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        updated = pd.concat([updated, new_df], ignore_index=True)

    # --- 3. Finalize and save ---
    out_path = Path(output_path) if output_path else Path(
        VALIDATION_SAMPLE).with_name('validation_sample_update.xlsx')
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure validation columns exist
    if 'is_valid_1' not in updated.columns:
        updated['is_valid_1'] = None
    if 'is_valid_2' not in updated.columns:
        updated['is_valid_2'] = None

    # Reorder columns to have old/new topic next to topic
    cols = list(df.columns)
    if 'topic' in cols:
        topic_idx = cols.index('topic')
        cols.insert(topic_idx + 1, 'old_topic')
        cols.insert(topic_idx + 2, 'new_topic')
    else:
        cols.extend(['topic', 'old_topic', 'new_topic'])
    
    # Add any columns from the new_df that are not in the original df
    final_cols = list(dict.fromkeys(cols + list(updated.columns)))
    updated = updated.reindex(columns=final_cols)


    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        updated.to_excel(writer, index=False, sheet_name='validation_sample')
        worksheet = writer.sheets['validation_sample']
        # Add data validation for is_valid columns if they exist
        for col_letter in ['E', 'F', 'G']: # Assuming is_valid_1/2 are F,G
            try:
                col_name = worksheet[f'{col_letter}1'].value
                if 'is_valid' in col_name:
                    dv = DataValidation(
                        type="list", formula1='"True,False"', allow_blank=True)
                    worksheet.add_data_validation(dv)
                    dv.add(f'{col_letter}2:{col_letter}{len(updated)+1}')
            except IndexError:
                continue # Column doesn't exist

    print(f"Validation sample regenerated and saved to {out_path}")
    return updated


if __name__ == '__main__':
    generate_stratum_table()
    validation_sample()
