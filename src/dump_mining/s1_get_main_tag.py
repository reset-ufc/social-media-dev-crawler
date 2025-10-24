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
    # Limpa o arquivo se ele já existir para garantir dados novos
    with open(COARSE_QUESTIONS, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(QUESTION_FEATURES)

def parse_posts_from_7z(site_alias):
    """Extrai e processa o Posts.xml, salvando perguntas com a QUESTION_TAG e retornando a contagem."""
    site_file = SITES[site_alias]
    archive_path = os.path.join(DUMP, site_file)

    if not os.path.exists(archive_path):
        logger.warning(f"[{site_alias}] Arquivo não encontrado: {archive_path}")
        return 0

    logger.info(f"[{site_alias}] Lendo arquivo compactado: {archive_path}")
    post_count = 0
    try:
        with py7zr.SevenZipFile(archive_path, mode='r') as archive:
            posts_files = [f for f in archive.getnames() if "Posts.xml" in f]
            if not posts_files:
                logger.warning(f"[{site_alias}] Nenhum Posts.xml dentro do .7z.")
                return 0

            temp_dir = tempfile.mkdtemp()
            archive.extract(path=temp_dir, targets=posts_files)
            posts_path = os.path.join(temp_dir, posts_files[0])

            logger.info(f"[{site_alias}] Processando {posts_path} e filtrando por tag '{QUESTION_TAG}'...")

            context = ET.iterparse(posts_path, events=("start",))
            for _, elem in context:
                if elem.tag != "row":
                    continue

                if elem.attrib.get("PostTypeId") == "1":  # Pergunta
                    tags_field = elem.attrib.get("Tags", "")
                    if not tags_field:
                        continue

                    tags = extract_tag_list(tags_field)
                    
                    if QUESTION_TAG in tags:
                        post_count += 1
                        tags_str = ";".join(tags)

                        def safe_int(value):
                            try:
                                return int(value)
                            except (ValueError, TypeError):
                                return 0

                        row = [
                            site_alias, tags_str, elem.attrib.get("Id", ""),
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
        logger.info(f"[{site_alias}] Posts encontrados com a tag '{QUESTION_TAG}': {post_count}")
    except Exception as e:
        logger.error(f"[{site_alias}] Erro ao processar {archive_path}: {e}", exc_info=True)
        return 0
    
    return post_count

def main():
    logger.info("Inicializando coleta de perguntas...")
    initiate_csv()

    site_post_counts = {}
    for site_alias in SITES.keys():
        count = parse_posts_from_7z(site_alias)
        site_post_counts[site_alias] = count

    logger.info("\n##### RESUMO FINAL DA ETAPA 1 #####")
    total_posts = 0
    for site, count in site_post_counts.items():
        logger.info(f"  - Site: {site}, Posts encontrados: {count}")
        total_posts += count
    logger.info(f"  - TOTAL DE POSTS ENCONTRADOS: {total_posts}")
    logger.info("##### FIM DO RESUMO #####\n")

    logger.info("Processamento concluído com sucesso!")


if __name__ == "__main__":
    main()
