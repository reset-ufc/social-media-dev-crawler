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
Requisito: Você precisa ter o 7zip instalado no seu sistema operacional
 Linux: sudo apt install p7zip-full.
 Windows: adicione o executável do 7-Zip ao seu PATH.
"""


def initiate_csv():
    ensure_parent_dir(COARSE_QUESTIONS)
    pd.DataFrame(columns=QUESTION_FEATURES).to_csv(
        COARSE_QUESTIONS,
        index=False,
        encoding="utf-8"
    )

def append_batch(batch_rows):
    if not batch_rows:
        return
    pd.DataFrame(batch_rows, columns=QUESTION_FEATURES).to_csv(
        COARSE_QUESTIONS,
        mode="a",
        header=False,
        index=False,
        encoding="utf-8"
    )

def parse_posts_from_7z(site_alias):
    site_file = SITES[site_alias]
    archive_path = os.path.join(DUMP, site_file)

    if not os.path.exists(archive_path):
        logger.warning(f"[{site_alias}] Arquivo não encontrado: {archive_path}")
        return 0

    posts_filename = "Posts.xml"
    post_count = 0
    
    logger.info(f"[{site_alias}] Iniciando Streaming do {posts_filename} via Pipe...")

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
            if QUESTION_TAG not in tags:
                elem.clear()
                continue

            post_count += 1
            batch.append([
                site_alias,
                ";".join(tags),
                elem.attrib.get("Id", ""),
            ])

            if len(batch) >= batch_size:
                append_batch(batch)
                batch.clear()

            elem.clear()

    append_batch(batch)

    logger.info(f"[{site_alias}] Concluído. Posts salvos: {post_count}")
    return post_count


def main():
    logger.info("Inicializando coleta otimizada (Zero-Disk-Usage)...")
    initiate_csv()
    for site_alias in SITES.keys():
        parse_posts_from_7z(site_alias)


if __name__ == "__main__":
    main()