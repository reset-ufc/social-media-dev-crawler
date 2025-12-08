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
    and enforcing stratum allocations.

    - Updates `new_topic` for existing posts based on `CLASSIFIED_POSTS`.
    - Adds `old_topic` and `new_topic` columns to track changes.
    - Removes posts from over-represented topics (rows deleted).
    - Reallocates posts from under-represented topics by moving excess posts
      from over-represented topics (within the same dataframe, no added rows).
    - For reallocated posts, clears is_valid_* columns and old_topic.
    - Removes the `topic` column from output.
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

    # Determine ID column
    if 'id' in updated.columns:
        id_col = 'id'
    elif 'question_id' in updated.columns:
        id_col = 'question_id'
    else:
        id_col = updated.columns[0]

    # Normalize IDs (remove decimal part if present)
    updated[id_col] = updated[id_col].astype(str).str.split('.').str[0]

    # --- 1. Add old_topic and new_topic columns ---
    if 'topic' not in updated.columns:
        updated['topic'] = pd.NA
    updated['old_topic'] = updated['topic'].copy()
    updated['new_topic'] = updated['topic'].copy()

    # Load classified posts and build topic mapping
    classified = pd.read_csv(CLASSIFIED_POSTS, dtype={'question_id': str})
    classified['question_id'] = classified['question_id'].str.split('.').str[0]
    topic_mapping = dict(zip(classified['question_id'], classified['topic']))

    # Update new_topic based on mapping (keep old if not found)
    for idx, row_id in enumerate(updated[id_col]):
        new_t = topic_mapping.get(str(row_id), updated.at[idx, 'new_topic'])
        updated.at[idx, 'new_topic'] = new_t

    # --- 2. Enforce stratum allocations by removing excess ---
    topic_counts = updated['new_topic'].value_counts().to_dict()
    indices_to_remove = []

    for topic, target in allocation_target.items():
        current = topic_counts.get(topic, 0)
        if current > target:
            excess = current - target
            topic_indices = updated[updated['new_topic']
                                    == topic].index.tolist()
            # Remove the first `excess` posts from this topic
            indices_to_remove.extend(topic_indices[:excess])

    updated = updated.drop(indices_to_remove).reset_index(drop=True)

    # --- 3. Reallocate posts from remaining excess to deficit topics ---
    topic_counts = updated['new_topic'].value_counts().to_dict()

    # Identify remaining excess and deficit
    excess_indices_by_topic = {}
    deficit_topics = {}
    for topic, target in allocation_target.items():
        current = topic_counts.get(topic, 0)
        if current > target:
            excess = current - target
            excess_indices = updated[updated['new_topic']
                                     == topic].index.tolist()
            # Last excess posts
            excess_indices_by_topic[topic] = excess_indices[-excess:]
        elif current < target:
            deficit = target - current
            deficit_topics[topic] = deficit

    # Reallocate excess posts to deficit topics
    for deficit_topic, deficit_count in deficit_topics.items():
        reallocated = 0
        for excess_topic, excess_indices in excess_indices_by_topic.items():
            if reallocated >= deficit_count:
                break
            for idx in excess_indices:
                if reallocated >= deficit_count:
                    break
                # Change this post's new_topic to deficit_topic
                updated.at[idx, 'new_topic'] = deficit_topic
                # Clear is_valid columns and old_topic for reallocated posts
                for col in updated.columns:
                    if 'is_valid' in col:
                        updated.at[idx, col] = None
                updated.at[idx, 'old_topic'] = None
                reallocated += 1

    # --- 4. Remove topic column and finalize ---
    if 'topic' in updated.columns:
        updated = updated.drop(columns=['topic'])

    # Reorder columns: old_topic and new_topic after id/link
    cols = list(updated.columns)
    if 'old_topic' in cols:
        cols.remove('old_topic')
    if 'new_topic' in cols:
        cols.remove('new_topic')

    # Insert after 'link' if it exists, else at the end
    if 'link' in cols:
        link_idx = cols.index('link')
        cols.insert(link_idx + 1, 'old_topic')
        cols.insert(link_idx + 2, 'new_topic')
    else:
        cols.extend(['old_topic', 'new_topic'])

    updated = updated[cols]

    # --- 5. Save to Excel ---
    out_path = Path(output_path) if output_path else Path(
        VALIDATION_SAMPLE).with_name('validation_sample_update.xlsx')
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        updated.to_excel(writer, index=False, sheet_name='validation_sample')
        worksheet = writer.sheets['validation_sample']

        # Add data validation for is_valid columns
        for idx, col in enumerate(updated.columns, start=1):
            if 'is_valid' in col:
                dv = DataValidation(
                    type="list", formula1='"True,False"', allow_blank=True)
                worksheet.add_data_validation(dv)
                # Convert 1-indexed to Excel column letter
                col_letter = chr(64 + idx)
                dv.add(f'{col_letter}2:{col_letter}{len(updated)+1}')

    print(f"Validation sample regenerated and saved to {out_path}")
    print(f"Total rows: {len(updated)}")
    final_counts = updated['new_topic'].value_counts().to_dict()
    for topic in sorted(allocation_target.keys()):
        target = allocation_target[topic]
        final = final_counts.get(topic, 0)
        status = "✓" if final == target else "✗"
        print(f"  {status} {topic}: {final}/{target}")

    return updated


if __name__ == '__main__':
    generate_stratum_table()
    validation_sample()
