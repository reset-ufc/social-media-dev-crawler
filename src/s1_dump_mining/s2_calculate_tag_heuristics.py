import sys
import os
import xml.etree.ElementTree as ET
import pandas as pd
from itertools import product
from collections import Counter
from typing import Tuple, Dict, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_global import *
from paths import *

logger = get_logger(__name__)

TAG_FEATURES = ['tag', 'b', 'a', 'h1', 'h2']
BATCH_SIZE = 10000


def initiate_csv(output_path: Optional[str] = None) -> None:
    """Initialize CSV file with required tag columns.

    Args:
        output_path: Output file path. Defaults to COARSE_QUESTIONS.
    """
    if output_path is None:
        output_path = COARSE_QUESTIONS
    ensure_parent_dir(output_path)
    pd.DataFrame(columns=TAG_FEATURES).to_csv(
        output_path,
        index=False,
        encoding="utf-8"
    )


def append_batch(batch_rows: list, output_path: Optional[str] = None) -> None:
    """Append batch of rows to CSV file.

    Args:
        batch_rows: List of rows to append.
        output_path: Output file path. Defaults to COARSE_QUESTIONS.
    """
    if not batch_rows:
        return
    if output_path is None:
        output_path = COARSE_QUESTIONS
    pd.DataFrame(batch_rows, columns=TAG_FEATURES).to_csv(
        output_path,
        mode="a",
        header=False,
        index=False,
        encoding="utf-8"
    )


def collect_tags_from_7z(site_alias: str, question_tag: str) -> Tuple[Counter, Counter]:
    """Collect all tags from a site and count their occurrences.

    Args:
        site_alias: Site alias to process.
        question_tag: The tag to use as reference for filtering.

    Returns:
        Tuple containing:
        - all_tags_counter: Counter with counts of all tags in all posts
        - question_tags_counter: Counter with counts of tags co-occurring with question_tag
    """
    site_file = SITES[site_alias]
    archive_path = os.path.join(DUMP, site_file)

    if not os.path.exists(archive_path):
        logger.warning(f"[{site_alias}] File not found: {archive_path}")
        return Counter(), Counter()

    all_tags_counter = Counter()
    question_tags_counter = Counter()

    logger.info(f"[{site_alias}] Starting tag collection from Posts.xml...")
    logger.info(f"[{site_alias}] Using question tag: '{question_tag}'")

    with stream_posts_from_7z(archive_path) as context:
        for event, elem in context:
            if elem.tag != "row":
                continue

            if elem.attrib.get("PostTypeId") != "1":
                elem.clear()
                continue

            tags_field = elem.attrib.get("Tags", "")
            if not tags_field:
                elem.clear()
                continue

            tags = extract_tag_list(tags_field)
            all_tags_counter.update(tags)

            if question_tag in tags:
                question_tags_counter.update(tags)

            elem.clear()

    logger.info(
        f"[{site_alias}] Unique tags (all posts): {len(all_tags_counter)}")
    logger.info(
        f"[{site_alias}] Unique tags (with {question_tag}): {len(question_tags_counter)}")

    return all_tags_counter, question_tags_counter


def calculate_tag_metrics(tag_data: Dict[str, Tuple[Counter, Counter]], question_tag: str) -> Dict[str, Dict[str, float]]:
    """Calculate metrics b, a, h1, h2 for each tag.

    Metrics:
    - b: number of posts containing the tag (across all data)
    - a: number of posts containing both the tag and question_tag
    - h1: a/b (proportion of posts with tag that also have question_tag)
    - h2: a/c (proportion of tag relative to total posts with question_tag)

    Args:
        tag_data: Dictionary mapping site_alias to (all_tags_counter, question_tags_counter)
        question_tag: The tag to use as reference for calculations.

    Returns:
        Dictionary with metrics per tag: {tag: {'b': x, 'a': y, 'h1': z, 'h2': w}}
    """
    global_all_tags = Counter()
    global_question_tags = Counter()

    for all_tags_counter, question_tags_counter in tag_data.values():
        global_all_tags.update(all_tags_counter)
        global_question_tags.update(question_tags_counter)

    total_posts_with_question = global_question_tags.get(question_tag, 0)

    if total_posts_with_question == 0:
        logger.warning(f"No posts with '{question_tag}' found!")
        return {}

    logger.info(
        f"Total posts with '{question_tag}': {total_posts_with_question}")

    tag_metrics = {}
    for tag in global_question_tags.keys():
        b = global_all_tags.get(tag, 0)
        a = global_question_tags.get(tag, 0)
        h1 = a / b if b > 0 else 0.0
        h2 = a / total_posts_with_question if total_posts_with_question > 0 else 0.0

        tag_metrics[tag] = {'b': b, 'a': a, 'h1': h1, 'h2': h2}

    return tag_metrics


def filter_tags_by_thresholds(
    tag_metrics: Dict[str, Dict[str, float]],
    threshold1: Optional[float] = None,
    threshold2: Optional[float] = None
) -> Dict[str, Dict[str, float]]:
    """Filter tags based on h1 and h2 thresholds.

    Args:
        tag_metrics: Dictionary with metrics per tag.
        threshold1: Minimum threshold for h1 (optional).
        threshold2: Minimum threshold for h2 (optional).

    Returns:
        Dictionary with filtered tags.
    """
    if threshold1 is None and threshold2 is None:
        return tag_metrics

    initial_count = len(tag_metrics)
    removed_by_h1 = 0
    removed_by_h2 = 0
    removed_by_both = 0

    filtered = {}
    for tag, metrics in tag_metrics.items():
        passes_h1 = True if threshold1 is None else metrics['h1'] >= threshold1
        passes_h2 = True if threshold2 is None else metrics['h2'] >= threshold2

        if passes_h1 and passes_h2:
            filtered[tag] = metrics
        else:
            if not passes_h1 and not passes_h2:
                removed_by_both += 1
            elif not passes_h1:
                removed_by_h1 += 1
            else:
                removed_by_h2 += 1

    logger.info(f"\nFiltering Statistics:")
    logger.info(f"  Initial tags: {initial_count}")
    logger.info(f"  Removed by h1 (h1 < {threshold1}): {removed_by_h1}")
    logger.info(f"  Removed by h2 (h2 < {threshold2}): {removed_by_h2}")
    logger.info(f"  Removed by both filters: {removed_by_both}")
    logger.info(f"  Final tags: {len(filtered)}")

    return filtered


def save_tags_to_csv(tag_metrics: Dict[str, Dict[str, float]], output_path: str) -> None:
    """Save tag metrics to CSV file.

    Args:
        tag_metrics: Dictionary with metrics per tag.
        output_path: Output file path.
    """
    rows = [
        [tag, metrics['b'], metrics['a'], metrics['h1'], metrics['h2']]
        for tag, metrics in sorted(tag_metrics.items())
    ]

    if rows:
        append_batch(rows, output_path)


def process_all_sites(
    output_path=R_TAGS,
    threshold1=THRE1,
    threshold2=THRE2,
    sites_to_process=None,
    question_tag=QUESTION_TAG) -> int:
    """Process specified sites and generate file with filtered tags.

    Args:
        output_path: Path to save results.
        threshold1: First threshold value.
        threshold2: Second threshold value.
        sites_to_process: List of site aliases to process. If None, processes all except crypto.
        question_tag: The tag to use as reference for filtering.

    Returns:
        Number of tags that passed the filters.
    """
    if sites_to_process is None:
        # Process all sites except crypto by default
        sites_to_process = [site for site in SITES.keys() if site != "crypto"]

    tag_data = {}
    for site_alias in sites_to_process:
        all_tags_counter, question_tags_counter = collect_tags_from_7z(
            site_alias, question_tag)
        if all_tags_counter or question_tags_counter:
            tag_data[site_alias] = (all_tags_counter, question_tags_counter)
            logger.info(f"  └─ [{site_alias}] Tags collected")

    logger.info("\nCalculating tag metrics...")
    tag_metrics = calculate_tag_metrics(tag_data, question_tag)
    logger.info(f"Total unique tags with {question_tag}: {len(tag_metrics)}")

    if threshold1 is not None or threshold2 is not None:
        logger.info(
            f"Applying filters: h1 >= {threshold1}, h2 >= {threshold2}")
        tag_metrics = filter_tags_by_thresholds(
            tag_metrics, threshold1, threshold2)
        logger.info(f"Tags after filtering: {len(tag_metrics)}")

    initiate_csv(output_path)
    save_tags_to_csv(tag_metrics, output_path)

    return len(tag_metrics)


def test_threshold_combinations(
    threshold_dir=None,
    sites_to_process=None,
    question_tag=QUESTION_TAG) -> None:
    """Test various threshold combinations and save results to separate files.

    Args:
        threshold_dir: Directory to save threshold test results.
        sites_to_process: List of site aliases to process.
        question_tag: The tag to use as reference for filtering.
    """
    _TREH1 = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    _TREH2 = [0.001, 0.002, 0.005, 0.010, 0.015, 0.020, 0.30]

    if threshold_dir is None:
        base_dir = os.path.dirname(COARSE_QUESTIONS)
        threshold_dir = os.path.join(base_dir, "threshold_combinations")
    
    os.makedirs(threshold_dir, exist_ok=True)

    if sites_to_process is None:
        sites_to_process = [site for site in SITES.keys() if site != "crypto"]

    logger.info("=" * 80)
    logger.info("STARTING THRESHOLD TESTS")
    logger.info(f"Sites to process: {sites_to_process}")
    logger.info(f"Question tag: '{question_tag}'")
    logger.info(f"Total combinations: {len(_TREH1) * len(_TREH2)}")
    logger.info("=" * 80)

    logger.info("\nCollecting tags from all sites...")
    tag_data = {}
    for site_alias in sites_to_process:
        all_tags_counter, question_tags_counter = collect_tags_from_7z(
            site_alias, question_tag)
        if all_tags_counter or question_tags_counter:
            tag_data[site_alias] = (all_tags_counter, question_tags_counter)
            logger.info(f"  └─ [{site_alias}] Tags collected")

    logger.info("\nCalculating tag metrics...")
    all_tag_metrics = calculate_tag_metrics(tag_data, question_tag)
    logger.info(f"Total unique tags: {len(all_tag_metrics)}")

    combinations = list(product(_TREH1, _TREH2))
    combination_stats = {}

    for idx, (thr1, thr2) in enumerate(combinations, 1):
        thr1_str = f"{thr1:.3f}".replace(".", "_")
        thr2_str = f"{thr2:.3f}".replace(".", "_")
        output_filename = f"TRH1_{thr1_str}_TRH2_{thr2_str}.csv"
        output_path = os.path.join(threshold_dir, output_filename)

        logger.info(
            f"\n[{idx}/{len(combinations)}] Processing TRH1={thr1}, TRH2={thr2}")
        logger.info(f"File: {output_filename}")

        filtered_tags = filter_tags_by_thresholds(all_tag_metrics, thr1, thr2)
        num_tags = len(filtered_tags)

        logger.info(f"  └─ Tags passed filters: {num_tags}")

        initiate_csv(output_path)
        save_tags_to_csv(filtered_tags, output_path)

        combination_key = f"TRH1_{thr1:.3f}_TRH2_{thr2:.3f}"
        combination_stats[combination_key] = {
            'thr1': thr1,
            'thr2': thr2,
            'num_tags': num_tags,
            'tags': sorted(filtered_tags.keys())
        }

    logger.info("\n" + "=" * 80)
    logger.info("THRESHOLD TESTS COMPLETED")
    logger.info(f"Files saved in: {threshold_dir}")
    logger.info("=" * 80)

    if combination_stats:
        _generate_summary_reports(combination_stats, threshold_dir)


def _generate_summary_reports(combination_stats: Dict, threshold_dir: str) -> None:
    """Generate summary reports for threshold test results.

    Args:
        combination_stats: Dictionary with statistics per combination.
        threshold_dir: Directory to save reports.
    """
    logger.info("\n" + "=" * 80)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 80)

    sorted_combinations = sorted(
        combination_stats.items(),
        key=lambda x: x[1]['num_tags']
    )

    max_comb = sorted_combinations[-1]
    logger.info(f"\nCOMBINATION WITH MOST TAGS:")
    logger.info(f"   {max_comb[0]}")
    logger.info(f"   Number of tags: {max_comb[1]['num_tags']}")
    logger.info(
        f"   Thresholds: h1 >= {max_comb[1]['thr1']}, h2 >= {max_comb[1]['thr2']}")

    min_comb = sorted_combinations[0]
    logger.info(f"\nCOMBINATION WITH FEWEST TAGS:")
    logger.info(f"   {min_comb[0]}")
    logger.info(f"   Number of tags: {min_comb[1]['num_tags']}")
    logger.info(
        f"   Thresholds: h1 >= {min_comb[1]['thr1']}, h2 >= {min_comb[1]['thr2']}")

    median_idx = len(sorted_combinations) // 2
    median_comb = sorted_combinations[median_idx]
    logger.info(f"\nMEDIAN COMBINATION:")
    logger.info(f"   {median_comb[0]}")
    logger.info(f"   Number of tags: {median_comb[1]['num_tags']}")
    logger.info(
        f"   Thresholds: h1 >= {median_comb[1]['thr1']}, h2 >= {median_comb[1]['thr2']}")

    logger.info("\n" + "=" * 80)

    comparison_path = os.path.join(
        threshold_dir, "combinations_comparison.csv")
    logger.info(f"\nCreating comparison file: {comparison_path}")

    max_tags_length = max(len(stats['tags'])
                          for stats in combination_stats.values())

    comparison_data = {}
    for comb_name, stats in sorted(combination_stats.items()):
        tags_list = stats['tags'] + [''] * \
            (max_tags_length - len(stats['tags']))
        comparison_data[comb_name] = tags_list

    comparison_df = pd.DataFrame(comparison_data)
    comparison_df.to_csv(comparison_path, index=False, encoding='utf-8')

    logger.info(f"✓ Comparison file created successfully")
    logger.info(
        f"  Dimensions: {comparison_df.shape[0]} rows × {comparison_df.shape[1]} columns")

    summary_path = os.path.join(threshold_dir, "combinations_summary.csv")
    summary_data = [
        {
            'combination': comb_name,
            'threshold1': stats['thr1'],
            'threshold2': stats['thr2'],
            'num_tags': stats['num_tags']
        }
        for comb_name, stats in sorted(combination_stats.items())
    ]

    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values('num_tags', ascending=False)
    summary_df.to_csv(summary_path, index=False, encoding='utf-8')

    logger.info(f"✓ Summary file created: {summary_path}")
    logger.info("=" * 80)


def main():
    """Main execution function."""
    logger.info("Initializing tag processing with heuristics...")

    # Process standard sites (stackoverflow and security)
    logger.info("\n" + "=" * 80)
    logger.info("### PROCESSING STANDARD SITES (stackoverflow, security) ###")
    logger.info("=" * 80)
    num_tags = process_all_sites(
        output_path=R_TAGS,
        threshold1=THRE1,
        threshold2=THRE2,
        sites_to_process=["stackoverflow", "security"],
        question_tag=QUESTION_TAG
    )
    logger.info(f"\nTotal tags saved in main file: {num_tags}")

    logger.info("\n### THRESHOLD TESTS FOR STANDARD SITES ###")
    base_dir = os.path.dirname(COARSE_QUESTIONS)
    threshold_dir_standard = os.path.join(base_dir, "threshold_combinations")
    test_threshold_combinations(
        threshold_dir=threshold_dir_standard,
        sites_to_process=["stackoverflow", "security"],
        question_tag=QUESTION_TAG
    )

    # Process crypto site separately
    logger.info("\n" + "=" * 80)
    logger.info("### PROCESSING CRYPTO SITE (crypto) ###")
    logger.info("=" * 80)
    num_tags_crypto = process_all_sites(
        output_path=R_TAGS_CRYPTO,
        threshold1=THRE1,
        threshold2=THRE2,
        sites_to_process=["crypto"],
        question_tag=QUESTION_TAG_CRYPTO
    )
    logger.info(f"\nTotal tags saved in crypto file: {num_tags_crypto}")

    logger.info("\n### THRESHOLD TESTS FOR CRYPTO SITE ###")
    threshold_dir_crypto = os.path.join(base_dir, "threshold_combinations_crypto")
    test_threshold_combinations(
        threshold_dir=threshold_dir_crypto,
        sites_to_process=["crypto"],
        question_tag=QUESTION_TAG_CRYPTO
    )

    logger.info("\n" + "=" * 80)
    logger.info("### PROCESSING COMPLETE ###")
    logger.info("=" * 80)
    logger.info(f"Standard sites - Tags saved: {num_tags}")
    logger.info(f"Crypto site - Tags saved: {num_tags_crypto}")


if __name__ == "__main__":
    main()