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


def get_related_tags_for_site(site_alias: str):
    """Lê as tags relacionadas para um site específico."""
    tags_path = get_releated_tags_path(site_alias)
    try:
        df = pd.read_csv(tags_path)
        return set(df['tag'])
    except FileNotFoundError:
        logger.error(
            f"Arquivo de tags relacionadas não encontrado para o site '{site_alias}': {tags_path}")
        return set()


def initialize_csv(path):
    """Cria o CSV com cabeçalho, se ainda não existir."""
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(POST_FEATURES)


def preload_commented_and_answered_posts(site_archive_path):
    """
    Lê os arquivos Comments.xml e Posts.xml uma vez para extrair todos os IDs
    de posts que têm comentários ou são respostas. Isso evita reabrir o .7z
    para cada post, melhorando drasticamente a performance.
    """
    commented_post_ids = set()
    answered_post_ids = set()
    temp_dir = tempfile.mkdtemp()
    try:
        with py7zr.SevenZipFile(site_archive_path, mode='r') as archive:
            targets = [f for f in archive.getnames() if f in [
                "Comments.xml", "Posts.xml"]]
            if not targets:
                return commented_post_ids, answered_post_ids

            archive.extract(path=temp_dir, targets=targets)

            # Processa Comments.xml
            comments_xml_path = os.path.join(temp_dir, "Comments.xml")
            if os.path.exists(comments_xml_path):
                context = ET.iterparse(comments_xml_path, events=("start",))
                for _, elem in context:
                    if elem.tag == "row":
                        post_id = elem.attrib.get("PostId")
                        if post_id:
                            commented_post_ids.add(post_id)
                    elem.clear()

            # Processa Posts.xml para encontrar respostas (ParentId)
            posts_xml_path = os.path.join(temp_dir, "Posts.xml")
            if os.path.exists(posts_xml_path):
                context = ET.iterparse(posts_xml_path, events=("start",))
                for _, elem in context:
                    if elem.tag == "row" and elem.attrib.get("PostTypeId") == "2":
                        parent_id = elem.attrib.get("ParentId")
                        if parent_id:
                            answered_post_ids.add(parent_id)
                    elem.clear()
                del context  # Garante que o arquivo XML seja liberado
    except Exception as e:
        logger.warning(f"Erro ao pré-carregar comentários/respostas: {e}")
    finally:
        shutil.rmtree(temp_dir)
    return commented_post_ids, answered_post_ids


def find_and_save_related_posts():
    """Procura e salva posts que tenham as tags relacionadas."""

    processed_posts = set()
    site_post_counts = {}
    file_post_counts = []

    initialize_csv(RELEATED_POSTS)

    for site_alias, site_name in SITES.items():
        logger.info(f"\n--- Processando site: {site_alias} ---")
        related_tags = get_related_tags_for_site(site_alias)
        if not related_tags:
            logger.warning(
                f"Nenhuma tag relacionada encontrada para '{site_alias}'. Pulando...")
            continue

        site_archive = os.path.join(DUMP, f"{site_name}")
        site_count = 0

        if not os.path.exists(site_archive):
            logger.warning(
                f"Arquivo compactado não encontrado para '{site_alias}' em: {site_archive}")
            continue

        logger.info(f"Processando: {site_archive}")

        with py7zr.SevenZipFile(site_archive, mode='r') as archive:
            # Assumimos que há apenas um Posts.xml por site
            posts_xml_path = "Posts.xml"
            if posts_xml_path not in archive.getnames():
                logger.warning(f"  Posts.xml não encontrado em {site_archive}")
                continue

            file_count = 0
            # Extrai para um diretório temporário para manter a compatibilidade
            temp_dir = tempfile.mkdtemp()
            try:
                archive.extract(path=temp_dir, targets=[posts_xml_path])
                xml_path = os.path.join(temp_dir, posts_xml_path)

                context = ET.iterparse(xml_path, events=("start",))
                for _, elem in context:
                    if elem.tag != "row":
                        continue

                    post_id = elem.attrib.get("Id")
                    if post_id in processed_posts:
                        elem.clear()
                        continue

                    tags_field = elem.attrib.get("Tags", "")
                    if tags_field:
                        # Correção: Extrai tags do formato <tag1><tag2>
                        post_tags = set(re.findall(r'<(.+?)>', tags_field))
                        if not related_tags.isdisjoint(post_tags):
                            row = [
                                site_alias,
                                ";".join(post_tags),
                                post_id,
                                elem.attrib.get(
                                    "AcceptedAnswerId", ""),
                                elem.attrib.get("AnswerCount", "0"),
                                safe_date(elem.attrib.get(
                                    "CreationDate", "")),
                                safe_date(elem.attrib.get(
                                    "LastActivityDate", "")),
                                safe_date(elem.attrib.get(
                                    "LastEditDate", "")),
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
                            file_count += 1

                    elem.clear()
                del context  # Garante que o arquivo XML seja liberado
            finally:
                shutil.rmtree(temp_dir)

            # registra quantos posts foram extraídos deste arquivo
            file_post_counts.append(
                (f"{site_alias}/{posts_xml_path}", file_count))

        site_post_counts[site_alias] = site_count

    logger.info("\nResumo final:")
    for site, count in site_post_counts.items():
        logger.info(f"  - {site}: {count} posts válidos")


def main():
    find_and_save_related_posts()
    logger.info("Processamento concluído!")


if __name__ == "__main__":
    main()
