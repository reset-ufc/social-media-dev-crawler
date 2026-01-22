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


BANNED_TAGS = {
    "stackoverflow": ('asn.1', 'bitcoin', 'entropy', 'javacard', 'secret-key', 'smartcard'),

    "crypto": ('adversarial-model', 'complexity', 'machine-learning', 'matrix-multiplication',
               'order-preserving', 'permutation'),

    "security": ('.net', 'algorithm', 'bitcoin', 'brute-force', 'compression', 'distributed-computing',
                  'drm', 'emv', 'government', 'instant-messaging', 'integrity', 'library', 'nist')
}


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


def filter_banned_tags(tag_metrics: Dict[str, Dict[str, float]], site_alias: str) -> Dict[str, Dict[str, float]]:
    """Remove banned tags for a specific site.

    Args:
        tag_metrics: Dictionary with metrics per tag.
        site_alias: Site alias to check for banned tags.

    Returns:
        Dictionary with banned tags removed.
    """
    if site_alias not in BANNED_TAGS:
        logger.info(f"[{site_alias}] No banned tags defined for this site")
        return tag_metrics
    
    banned_set = set(BANNED_TAGS[site_alias])
    initial_count = len(tag_metrics)
    
    present_banned_tags = banned_set & set(tag_metrics.keys())
    
    filtered = {tag: metrics for tag, metrics in tag_metrics.items() 
                if tag not in banned_set}
    
    removed_count = initial_count - len(filtered)
    
    if removed_count > 0:
        logger.info(f"\n[{site_alias}] === BANNED TAGS REMOVAL ===")
        logger.info(f"[{site_alias}] Total tags before filtering: {initial_count}")
        logger.info(f"[{site_alias}] Banned tags removed: {removed_count}")
        logger.info(f"[{site_alias}] Tags remaining: {len(filtered)}")
        if present_banned_tags:
            logger.info(f"[{site_alias}] Removed tags list: {sorted(present_banned_tags)}")
    else:
        logger.info(f"[{site_alias}] No banned tags found in the results")
    
    return filtered


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


def process_single_site(
    site_alias: str,
    output_path: str,
    threshold1: float,
    threshold2: float,
    question_tag: str) -> int:
    """Process a single site and generate file with filtered tags.

    Args:
        site_alias: Site alias to process.
        output_path: Path to save results.
        threshold1: First threshold value.
        threshold2: Second threshold value.
        question_tag: The tag to use as reference for filtering.

    Returns:
        Number of tags that passed the filters.
    """
    logger.info(f"\n[{site_alias}] Starting processing...")
    
    all_tags_counter, question_tags_counter = collect_tags_from_7z(
        site_alias, question_tag)
    
    if not all_tags_counter and not question_tags_counter:
        logger.warning(f"[{site_alias}] No tags collected")
        return 0

    tag_data = {site_alias: (all_tags_counter, question_tags_counter)}

    logger.info(f"[{site_alias}] Calculating tag metrics...")
    tag_metrics = calculate_tag_metrics(tag_data, question_tag)
    logger.info(f"[{site_alias}] Total unique tags with '{question_tag}': {len(tag_metrics)}")

    if threshold1 is not None or threshold2 is not None:
        logger.info(
            f"[{site_alias}] Applying filters: h1 >= {threshold1}, h2 >= {threshold2}")
        tag_metrics = filter_tags_by_thresholds(
            tag_metrics, threshold1, threshold2)
        logger.info(f"[{site_alias}] Tags after threshold filtering: {len(tag_metrics)}")

    tag_metrics = filter_banned_tags(tag_metrics, site_alias)

    initiate_csv(output_path)
    save_tags_to_csv(tag_metrics, output_path)

    return len(tag_metrics)


def test_threshold_combinations_single_site(
    site_alias: str,
    threshold_dir: str,
    question_tag: str) -> None:
    """Test various threshold combinations for a single site and save results to separate files.

    Args:
        site_alias: Site alias to process.
        threshold_dir: Directory to save threshold test results.
        question_tag: The tag to use as reference for filtering.
    """
    _TREH1 = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    _TREH2 = [0.001, 0.002, 0.005, 0.010, 0.015, 0.020, 0.30]

    os.makedirs(threshold_dir, exist_ok=True)

    logger.info("=" * 80)
    logger.info(f"STARTING THRESHOLD TESTS FOR {site_alias.upper()}")
    logger.info(f"Question tag: '{question_tag}'")
    logger.info(f"Total combinations: {len(_TREH1) * len(_TREH2)}")
    logger.info("=" * 80)

    logger.info(f"\n[{site_alias}] Collecting tags...")
    all_tags_counter, question_tags_counter = collect_tags_from_7z(
        site_alias, question_tag)
    
    if not all_tags_counter and not question_tags_counter:
        logger.warning(f"[{site_alias}] No tags collected. Skipping threshold tests.")
        return

    tag_data = {site_alias: (all_tags_counter, question_tags_counter)}

    logger.info(f"\n[{site_alias}] Calculating tag metrics...")
    all_tag_metrics = calculate_tag_metrics(tag_data, question_tag)
    logger.info(f"[{site_alias}] Total unique tags: {len(all_tag_metrics)}")

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
    logger.info(f"THRESHOLD TESTS COMPLETED FOR {site_alias.upper()}")
    logger.info(f"Files saved in: {threshold_dir}")
    logger.info("=" * 80)

    if combination_stats:
        _generate_summary_reports(combination_stats, threshold_dir, site_alias)


def _generate_summary_reports(combination_stats: Dict, threshold_dir: str, site_alias: str) -> None:
    """Generate summary reports for threshold test results.

    Args:
        combination_stats: Dictionary with statistics per combination.
        threshold_dir: Directory to save reports.
        site_alias: Site alias being processed.
    """
    logger.info("\n" + "=" * 80)
    logger.info(f"RESULTS SUMMARY FOR {site_alias.upper()}")
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
    logger.info("\n" + "=" * 80)
    logger.info("### PROCESSING ALL SITES INDIVIDUALLY ###")
    logger.info("=" * 80)

    results = {}

    # Process each site individually
    for site_alias in SITES.keys():
        logger.info("\n" + "=" * 80)
        logger.info(f"### PROCESSING SITE: {site_alias.upper()} ###")
        logger.info("=" * 80)

        # Get the appropriate question tag for this site
        question_tags_list = QUESTION_TAGS.get(site_alias, [QUESTION_TAG])
        question_tag = question_tags_list[0] if question_tags_list else QUESTION_TAG

        # Define output path for this site
        output_path = DATA_MINING_S1 / f"releated_tags_{site_alias}.csv"

        # Get site-specific thresholds
        if site_alias not in THRES:
            logger.warning(
                f"[{site_alias}] No thresholds defined in THRES. "
                "Skipping site."
            )
            continue

        threshold1, threshold2 = THRES[site_alias]

        logger.info(
            f"[{site_alias}] Using thresholds: "
            f"h1 >= {threshold1}, h2 >= {threshold2}"
        )

        num_tags = process_single_site(
            site_alias=site_alias,
            output_path=str(output_path),
            threshold1=threshold1,
            threshold2=threshold2,
            question_tag=question_tag
        )
        
        results[site_alias] = {
            'num_tags': num_tags,
            'question_tag': question_tag,
            'output_file': str(output_path)
        }

        logger.info(f"\n[{site_alias}] Total tags saved: {num_tags}")
        logger.info(f"[{site_alias}] Output file: {output_path}")

        # Run threshold tests for this site
        logger.info(f"\n### THRESHOLD TESTS FOR {site_alias.upper()} ###")
        threshold_dir_site = DATA_MINING_S1 / f"threshold_combinations_{site_alias}"
        test_threshold_combinations_single_site(
            site_alias=site_alias,
            threshold_dir=str(threshold_dir_site),
            question_tag=question_tag
        )

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("### PROCESSING COMPLETE - SUMMARY ###")
    logger.info("=" * 80)
    
    for site_alias, result in results.items():
        logger.info(f"\n{site_alias.upper()}:")
        logger.info(f"  Question tag: '{result['question_tag']}'")
        logger.info(f"  Tags saved: {result['num_tags']}")
        logger.info(f"  Output file: {result['output_file']}")

    logger.info("\n" + "=" * 80)
    logger.info("All sites processed successfully!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()