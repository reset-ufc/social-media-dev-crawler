import sys
import os
import subprocess  
import xml.etree.ElementTree as ET
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils_global import *
from paths import *

logger = get_logger(__name__)

QUESTION_FEATURES = ['site', 'tags', 'question_id']

"""
Requirement: You need to have 7zip installed on your operating system
 Linux: sudo apt install p7zip-full.
 Windows: add the 7-Zip executable to your PATH.
"""


def initiate_csv(output_path):
    """Initialize CSV file with headers"""
    ensure_parent_dir(output_path)
    pd.DataFrame(columns=QUESTION_FEATURES).to_csv(
        output_path,
        index=False,
        encoding="utf-8"
    )

def append_batch(batch_rows, output_path):
    """Append batch of rows to CSV file"""
    if not batch_rows:
        return
    pd.DataFrame(batch_rows, columns=QUESTION_FEATURES).to_csv(
        output_path,
        mode="a",
        header=False,
        index=False,
        encoding="utf-8"
    )

def parse_posts_from_7z(site_alias):
    """
    Parse posts from 7z archive for a specific site.
    Uses different tags and output files for crypto site.
    """
    site_file = SITES[site_alias]
    archive_path = os.path.join(DUMP, site_file)

    if not os.path.exists(archive_path):
        logger.warning(f"[{site_alias}] File not found: {archive_path}")
        return 0

    # Determine which tags to use for this site
    tags_to_search = QUESTION_TAGS.get(site_alias, [QUESTION_TAG])
    
    # Determine output file based on site
    if site_alias == "crypto":
        output_file = COARSE_QUESTIONS_CRYPTO
    else:
        output_file = COARSE_QUESTIONS

    posts_filename = "Posts.xml"
    post_count = 0
    
    logger.info(f"[{site_alias}] Starting streaming of {posts_filename} via Pipe...")
    logger.info(f"[{site_alias}] Searching for tags: {tags_to_search}")
    logger.info(f"[{site_alias}] Output file: {output_file}")

    batch = []
    batch_size = 1000

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
            
            # Check if any of the required tags is present
            if not any(tag in tags for tag in tags_to_search):
                elem.clear()
                continue

            post_count += 1
            batch.append([
                site_alias,
                ";".join(tags),
                elem.attrib.get("Id", ""),
            ])

            if len(batch) >= batch_size:
                append_batch(batch, output_file)
                batch.clear()

            elem.clear()

    append_batch(batch, output_file)

    logger.info(f"[{site_alias}] Completed. Posts saved: {post_count}")
    return post_count


def main():
    logger.info("Initializing optimized collection (Zero-Disk-Usage)...")
    
    # Initialize separate CSV files
    logger.info("Initializing main questions file...")
    initiate_csv(COARSE_QUESTIONS)
    
    logger.info("Initializing crypto-specific questions file...")
    initiate_csv(COARSE_QUESTIONS_CRYPTO)
    
    # Process each site
    for site_alias in SITES.keys():
        parse_posts_from_7z(site_alias)
    
    logger.info("Data collection completed successfully.")


if __name__ == "__main__":
    main()