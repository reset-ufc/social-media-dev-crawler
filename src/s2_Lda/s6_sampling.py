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
    """Regenerate validation sample keeping existing non-topic columns but
    updating the `topic` column to the current topics from `CLASSIFIED_POSTS`.
    Additionally, enforce stratum allocations: remove excess posts from over-allocated
    topics and add missing posts from under-allocated topics.

    Reads `VALIDATION_SAMPLE` (Excel), looks up each `id` (or `question_id`) in
    `CLASSIFIED_POSTS` and replaces the `topic` column with the current value
    when available. Writes the updated sheet to
    `validation_sample_update.xlsx` (or `output_path` if provided).
    Returns the updated DataFrame.
    """
    in_path = Path(VALIDATION_SAMPLE)
    if not in_path.exists():
        raise FileNotFoundError(f"Validation sample not found at {in_path}")

    # Load stratum table for allocation targets
    if not Path(STRATUM_TABLE).exists():
        raise FileNotFoundError(f"Stratum table not found at {STRATUM_TABLE}")
    stratum_df = pd.read_csv(STRATUM_TABLE)
    if 'topic' not in stratum_df.columns or 'allocated_nh' not in stratum_df.columns:
        raise ValueError(
            "STRATUM_TABLE must contain 'topic' and 'allocated_nh' columns")

    # build allocation target mapping
    allocation_target = dict(
        zip(stratum_df['topic'], stratum_df['allocated_nh']))

    # read existing validation sample
    df = pd.read_excel(in_path)

    # determine id column
    if 'id' in df.columns:
        id_col = 'id'
    elif 'question_id' in df.columns:
        id_col = 'question_id'
    else:
        # fallback to first column
        id_col = df.columns[0]

    # normalize ids to string for safe matching
    df[id_col] = df[id_col].astype(object).where(pd.notna(df[id_col]), None)
    ids = [str(int(x)) if (x is not None and isinstance(x, float) and x.is_integer(
    )) else str(x) for x in df[id_col].fillna('').tolist()]

    # load current classified posts and build mapping
    if not Path(CLASSIFIED_POSTS).exists():
        raise FileNotFoundError(
            f"Classified posts CSV not found at {CLASSIFIED_POSTS}")
    classified = pd.read_csv(CLASSIFIED_POSTS, dtype={'question_id': object})
    # ensure question_id as str
    if 'question_id' in classified.columns:
        classified['question_id'] = classified['question_id'].astype(
            object).where(pd.notna(classified['question_id']), None)
        classified['qid_str'] = classified['question_id'].apply(lambda x: str(int(x)) if (
            x is not None and isinstance(x, float) and x.is_integer()) else str(x) if x is not None else '')
        mapping = dict(zip(classified['qid_str'], classified.get(
            'topic', pd.Series([''] * len(classified)))))
    else:
        mapping = {}

    # create updated dataframe copying existing values, but updating topic when found
    updated = df.copy()
    # ensure there is a 'topic' column to update; if not, create it
    if 'topic' not in updated.columns:
        updated['topic'] = pd.NA

    for idx, val in enumerate(df[id_col].fillna('')):
        key = ids[idx]
        if key and key in mapping and pd.notna(mapping[key]):
            updated.at[idx, 'topic'] = mapping[key]
        # else keep existing value (already present in updated)

    # Now enforce allocations: count current topic distribution
    topic_counts = updated['topic'].value_counts().to_dict()

    # Identify topics with excess and deficit
    excess_per_topic = {}
    deficit_per_topic = {}

    for topic, target in allocation_target.items():
        current = topic_counts.get(topic, 0)
        if current > target:
            excess_per_topic[topic] = current - target
        elif current < target:
            deficit_per_topic[topic] = target - current

    # Remove excess posts from over-allocated topics
    for topic, excess_count in excess_per_topic.items():
        indices_to_remove = updated[updated['topic'] == topic].index.tolist()
        removed = 0
        for idx in indices_to_remove:
            if removed >= excess_count:
                break
            updated = updated.drop(idx)
            removed += 1

    updated = updated.reset_index(drop=True)

    # Add missing posts from classified_df for under-allocated topics
    if deficit_per_topic:
        # Get current ids in validation sample (as set)
        current_ids_set = set(ids)

        for topic, deficit_count in deficit_per_topic.items():
            # Find candidates from classified not yet in updated
            candidates = classified[
                (classified['topic'] == topic) &
                (classified['type'] == 'question') &
                (~classified['question_id'].astype(str).isin(current_ids_set))
            ].copy()

            if candidates.empty:
                print(
                    f"Warning: No additional candidates for topic '{topic}' (deficit={deficit_count})")
                continue

            # Sample up to deficit_count posts
            sample_size = min(deficit_count, len(candidates))
            sampled = candidates.sample(n=sample_size, replace=False)

            # Build rows to append (matching column structure of updated)
            new_rows = []
            for _, row in sampled.iterrows():
                new_row = {}
                for col in updated.columns:
                    if col == 'id' or col == 'question_id':
                        new_row[col] = row.get('question_id', '')
                    elif col == 'site':
                        new_row[col] = row.get('site_alias', '')
                    elif col == 'topic':
                        new_row[col] = topic
                    elif col == 'link':
                        qid = row.get('question_id', '')
                        site = row.get('site_alias', '')
                        try:
                            qid_str = str(int(qid))
                        except Exception:
                            qid_str = str(qid)
                        if str(site) == 'stackoverflow':
                            domain = 'stackoverflow.com'
                        else:
                            domain = f"{site}.stackexchange.com"
                        new_row[col] = f"https://{domain}/questions/{qid_str}"
                    elif col == 'is_valid':
                        new_row[col] = None
                    else:
                        new_row[col] = row.get(col, '')
                new_rows.append(new_row)

            # Append rows
            if new_rows:
                new_df = pd.DataFrame(new_rows)
                updated = pd.concat([updated, new_df], ignore_index=True)
                current_ids_set.update(
                    [str(x) for x in sampled['question_id'].tolist()])

    # choose output path
    if output_path:
        out_path = Path(output_path)
    else:
        out_path = Path(VALIDATION_SAMPLE).with_name(
            'validation_sample_update.xlsx')

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # write to Excel with data validation for is_valid if present
    try:
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            updated.to_excel(writer, index=False,
                             sheet_name='validation_sample')
            workbook = writer.book
            worksheet = writer.sheets['validation_sample']
            if 'is_valid' in updated.columns:
                from openpyxl.worksheet.datavalidation import DataValidation
                dv = DataValidation(
                    type="list", formula1='"True,False"', allow_blank=True)
                worksheet.add_data_validation(dv)
                dv.add(f'E2:E{len(updated)+1}')
    except Exception as e:
        # fallback: try to write without data validation
        updated.to_excel(out_path, index=False, sheet_name='validation_sample')

    # Log final allocation status
    final_counts = updated['topic'].value_counts().to_dict()
    print(f"\n=== Final Allocation Status ===")
    for topic in sorted(allocation_target.keys()):
        target = allocation_target[topic]
        final = final_counts.get(topic, 0)
        status = "✓" if final == target else "✗"
        print(f"{status} {topic}: {final}/{target}")

    return updated


if __name__ == '__main__':
    generate_stratum_table()
    validation_sample()
