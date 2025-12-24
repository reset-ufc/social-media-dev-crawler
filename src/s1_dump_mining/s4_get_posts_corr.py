import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
import tempfile
import py7zr
import re
import xml.etree.ElementTree as ET
import pandas as pd
import csv
from paths import *
from utils_global import *


logger = get_logger(__name__)

POST_FEATURES = [
    'site_alias', 'tags', 'question_id', 'accepted_answer_id', 'answer_count',
    'creation_date', 'last_activity_date', 'last_edit_date',
    'owner_id', 'score', 'view_count', 'title', 'body',
    'local_id', 'site'
]


def get_all_related_tags():
    """Lê todas as tags relacionadas do arquivo consolidado R_TAGS."""
    try:
        df = pd.read_csv(R_TAGS)
        related_tags = set(df['tag'])
        logger.info(f"Total de tags relacionadas carregadas: {len(related_tags)}")
        return related_tags
    except FileNotFoundError:
        logger.error(f"Arquivo de tags relacionadas não encontrado: {R_TAGS}")
        return set()
    except Exception as e:
        logger.error(f"Erro ao ler arquivo de tags relacionadas: {e}")
        return set()


def initialize_csv(path):
    """Cria o CSV com cabeçalho, se ainda não existir."""
    if not os.path.exists(path):
        ensure_parent_dir(path)
        with open(path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(POST_FEATURES)


def find_and_save_related_posts():
    """Procura e salva posts que tenham ao menos uma das tags relacionadas."""

    # Carrega todas as tags relacionadas uma única vez
    related_tags = get_all_related_tags()
    
    if not related_tags:
        logger.error("Nenhuma tag relacionada encontrada. Abortando processamento.")
        return

    processed_posts = set()
    site_post_counts = {}

    initialize_csv(RELEATED_POSTS)

    for site_alias, site_name in SITES.items():
        logger.info(f"\n--- Processando site: {site_alias} ---")

        site_archive = os.path.join(DUMP, f"{site_name}")
        site_count = 0

        if not os.path.exists(site_archive):
            logger.warning(
                f"Arquivo compactado não encontrado para '{site_alias}' em: {site_archive}")
            continue

        logger.info(f"Processando: {site_archive}")

        try:
            with py7zr.SevenZipFile(site_archive, mode='r') as archive:
                posts_xml_path = "Posts.xml"
                if posts_xml_path not in archive.getnames():
                    logger.warning(f"  Posts.xml não encontrado em {site_archive}")
                    continue

                # Extrai para um diretório temporário
                temp_dir = tempfile.mkdtemp()
                try:
                    archive.extract(path=temp_dir, targets=[posts_xml_path])
                    xml_path = os.path.join(temp_dir, posts_xml_path)

                    context = ET.iterparse(xml_path, events=("start",))
                    for _, elem in context:
                        if elem.tag != "row":
                            continue

                        # Processa apenas perguntas (PostTypeId = 1)
                        if elem.attrib.get("PostTypeId") != "1":
                            elem.clear()
                            continue

                        post_id = elem.attrib.get("Id")
                        if post_id in processed_posts:
                            elem.clear()
                            continue

                        tags_field = elem.attrib.get("Tags", "")
                        if tags_field:
                            # Extrai tags do formato <tag1><tag2>
                            post_tags = set(extract_tag_list(tags_field))
                            
                            # Verifica se há interseção entre as tags do post e as tags relacionadas
                            if not related_tags.isdisjoint(post_tags):
                                row = [
                                    site_alias,
                                    ";".join(post_tags),
                                    post_id,
                                    elem.attrib.get("AcceptedAnswerId", ""),
                                    elem.attrib.get("AnswerCount", "0"),
                                    safe_date(elem.attrib.get("CreationDate", "")),
                                    safe_date(elem.attrib.get("LastActivityDate", "")),
                                    safe_date(elem.attrib.get("LastEditDate", "")),
                                    elem.attrib.get("OwnerUserId", ""),
                                    elem.attrib.get("Score", "0"),
                                    elem.attrib.get("ViewCount", "0"),
                                    elem.attrib.get("Title", ""),
                                    elem.attrib.get("Body", ""),
                                    post_id,
                                    site_name
                                ]

                                with open(RELEATED_POSTS, "a", encoding="utf-8", newline="") as f_csv:
                                    csv.writer(f_csv).writerow(row)

                                processed_posts.add(post_id)
                                site_count += 1

                        elem.clear()
                    del context
                finally:
                    shutil.rmtree(temp_dir)

        except Exception as e:
            logger.error(f"Erro ao processar {site_archive}: {e}", exc_info=True)
            continue

        site_post_counts[site_alias] = site_count
        logger.info(f"  Posts encontrados com tags relacionadas: {site_count}")

    logger.info("\n##### RESUMO FINAL #####")
    total_posts = 0
    for site, count in site_post_counts.items():
        logger.info(f"  - {site}: {count} posts válidos")
        total_posts += count
    logger.info(f"  - TOTAL DE POSTS ENCONTRADOS: {total_posts}")
    logger.info("##### FIM DO RESUMO #####\n")


def main():
    logger.info("Iniciando busca de posts relacionados...")
    find_and_save_related_posts()
    logger.info("Processamento concluído!")


if __name__ == "__main__":
    main()