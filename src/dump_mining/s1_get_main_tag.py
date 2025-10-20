import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import *
from paths import *
import csv
import xml.etree.ElementTree as ET
import py7zr
import tempfile
import shutil


logger = get_logger(__name__)


# Estrutura completa de atributos conforme o StackExchange Data Dump atual
QUESTION_FEATURES = [
    'site', 'tags', 'question_id', 'accepted_answer_id', 'answer_count',
    'comment_count', 'favorite_count', 'creation_date', 'last_activity_date',
    'last_edit_date', 'owner_id', 'score', 'view_count',
    'title', 'body'
]


def initiate_csv():
    """Cria o CSV principal com cabeçalhos, se não existir."""
    ensure_parent_dir(COARSE_QUESTIONS)
    if not os.path.exists(COARSE_QUESTIONS):
        with open(COARSE_QUESTIONS, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(QUESTION_FEATURES)


def parse_posts_from_7z(site_alias):
    """Extrai e processa o Posts.xml de dentro do .7z"""
    site_file = SITES[site_alias]
    archive_path = os.path.join(DUMP, site_file)

    if not os.path.exists(archive_path):
        logger.warning(
            f"[{site_alias}] Arquivo não encontrado: {archive_path}")
        return

    logger.info(f"[{site_alias}] Lendo arquivo compactado: {archive_path}")

    try:
        with py7zr.SevenZipFile(archive_path, mode='r') as archive:
            posts_files = [f for f in archive.getnames() if "Posts.xml" in f]
            if not posts_files:
                print(f"[{site_alias}] Nenhum Posts.xml dentro do .7z.")
                return

            temp_dir = tempfile.mkdtemp()
            archive.extract(path=temp_dir, targets=posts_files)
            posts_path = os.path.join(temp_dir, posts_files[0])

            logger.info(f"[{site_alias}] Processando {posts_path} ...")

            context = ET.iterparse(posts_path, events=("start",))
            for _, elem in context:
                if elem.tag != "row":
                    continue

                if elem.attrib.get("PostTypeId") == "1":  # Pergunta
                    tags_field = elem.attrib.get("Tags", "")
                    if not tags_field:
                        continue

                    tags = extract_tag_list(tags_field)
                    tags_str = ";".join(tags)

                    def safe_int(value):
                        try:
                            return int(value)
                        except:
                            return 0

                    row = [
                        site_alias,
                        tags_str,
                        elem.attrib.get("Id", ""),
                        elem.attrib.get("AcceptedAnswerId", ""),
                        safe_int(elem.attrib.get("AnswerCount", 0)),
                        safe_int(elem.attrib.get("CommentCount", 0)),
                        safe_int(elem.attrib.get("FavoriteCount", 0)),
                        safe_date(elem.attrib.get("CreationDate", "")),
                        safe_date(elem.attrib.get("LastActivityDate", "")),
                        safe_date(elem.attrib.get("LastEditDate", "")),
                        elem.attrib.get("OwnerUserId", ""),
                        safe_int(elem.attrib.get("Score", 0)),
                        safe_int(elem.attrib.get("ViewCount", 0)),
                        elem.attrib.get("Title", ""),
                        elem.attrib.get("Body", "")
                    ]

                    with open(COARSE_QUESTIONS, "a", encoding="utf-8", newline="") as f:
                        csv.writer(f).writerow(row)

                elem.clear()

            del context
            shutil.rmtree(temp_dir)

    except Exception as e:
        logger.error(
            f"[{site_alias}] Erro ao processar {archive_path}: {e}", exc_info=True)


def main():
    logger.info("Inicializando coleta de perguntas...")
    initiate_csv()

    for site_alias in SITES.keys():
        parse_posts_from_7z(site_alias)

    logger.info("Processamento concluído com sucesso!")


if __name__ == "__main__":
    main()
