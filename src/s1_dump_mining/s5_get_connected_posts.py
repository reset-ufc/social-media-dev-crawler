import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils_global import safe_date
from paths import DUMP, CONNECTED_POSTS, RELEATED_POSTS, SITES
import csv
import pandas as pd
import xml.etree.ElementTree as ET
import tempfile
import py7zr
import shutil
from utils_global import get_logger

logger = get_logger(__name__)

POST_FEATURES = [
    "site_alias", "tags", "question_id", "accepted_answer_id", "answer_count",
    "creation_date", "last_activity_date", "last_edit_date",
    "owner_id", "score", "view_count", "comment_count",
    "title", "body", "site", "id", "type"
]

def write_csv_header():
    """Cria o arquivo CONNECTED_POSTS com cabeçalho."""
    os.makedirs(os.path.dirname(CONNECTED_POSTS), exist_ok=True)
    with open(CONNECTED_POSTS, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(POST_FEATURES)

def append_to_csv(row):
    """Adiciona uma linha ao CSV de posts conectados."""
    with open(CONNECTED_POSTS, "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(row)

def get_relevant_questions():
    """Lê o arquivo RELEATED_POSTS e retorna as perguntas-base."""
    try:
        df = pd.read_csv(RELEATED_POSTS, dtype=str)
        # Garante a compatibilidade de nomes de coluna
        if "question_id" not in df.columns and "id" in df.columns:
            df.rename(columns={"id": "question_id"}, inplace=True)
        return df
    except Exception as e:
        logger.error(f"Não foi possível carregar {RELEATED_POSTS}: {e}", exc_info=True)
        return pd.DataFrame()

def extract_posts_and_comments():
    """Extrai perguntas, respostas e comentários para o arquivo CONNECTED_POSTS."""
    questions_df = get_relevant_questions()
    if questions_df.empty:
        logger.warning("Nenhuma pergunta relevante encontrada em releated_posts.csv.")
        return

    write_csv_header()

    total_questions, total_answers, total_comments_written = 0, 0, 0

    for site_alias, site_file in SITES.items():
        logger.info(f"\n--- Processando site: {site_alias} ---")
        archive_path = os.path.join(DUMP, site_file)
        if not os.path.exists(archive_path):
            logger.warning(f"[{site_alias}] Arquivo de dump não encontrado: {archive_path}")
            continue

        site_questions_df = questions_df[questions_df["site_alias"] == site_alias]
        if site_questions_df.empty:
            logger.info(f"[{site_alias}] Nenhuma pergunta relevante para este site.")
            continue

        relevant_question_ids = set(site_questions_df["question_id"].values)
        
        temp_dir = tempfile.mkdtemp()
        try:
            with py7zr.SevenZipFile(archive_path, mode="r") as archive:
                targets = [f for f in archive.getnames() if f in ["Posts.xml", "Comments.xml"]]
                if not targets:
                    logger.warning(f"[{site_alias}] Posts.xml ou Comments.xml não encontrados no dump.")
                    continue
                archive.extract(path=temp_dir, targets=targets)

            # 1. Find answers and store them, and create answer_id -> question_id map
            answers = []
            found_answer_ids = set()
            answer_id_to_question_id = {}
            posts_path = os.path.join(temp_dir, "Posts.xml")
            if os.path.exists(posts_path):
                context = ET.iterparse(posts_path, events=("start",))
                for _, elem in context:
                    if elem.tag == "row" and elem.attrib.get("PostTypeId") == "2":
                        parent_id = elem.attrib.get("ParentId")
                        if parent_id in relevant_question_ids:
                            answer_attrib = elem.attrib
                            answers.append(answer_attrib)
                            answer_id = answer_attrib.get("Id")
                            if answer_id:
                                found_answer_ids.add(answer_id)
                                answer_id_to_question_id[answer_id] = parent_id
                    elem.clear()

            # 2. Find and store comments, and count them
            comments = []
            comment_counter = {}
            comments_path = os.path.join(temp_dir, "Comments.xml")
            if os.path.exists(comments_path):
                posts_to_get_comments_for = relevant_question_ids.union(found_answer_ids)
                context = ET.iterparse(comments_path, events=("start",))
                for _, elem in context:
                    if elem.tag == "row":
                        post_id = elem.attrib.get("PostId")
                        if post_id in posts_to_get_comments_for:
                            comments.append(elem.attrib)
                            comment_counter[post_id] = comment_counter.get(post_id, 0) + 1
                    elem.clear()
            
            # 3. Write questions to CSV
            for _, q in site_questions_df.iterrows():
                qid = q.get("question_id", "")
                q_comments = comment_counter.get(qid, 0)
                row = [
                    q.get("site_alias", ""), q.get("tags", ""), qid,
                    q.get("accepted_answer_id", ""), q.get("answer_count", "0"),
                    q.get("creation_date", ""), q.get("last_activity_date", ""),
                    q.get("last_edit_date", ""), q.get("owner_id", ""),
                    q.get("score", "0"), q.get("view_count", "0"), q_comments,
                    q.get("title", ""), q.get("body", ""), q.get("site", ""),
                    qid, "question"
                ]
                append_to_csv(row)
                total_questions += 1

            # 4. Write answers to CSV
            site_answers_written = 0
            for answer_attrib in answers:
                answer_id = answer_attrib.get("Id", "")
                parent_id = answer_attrib.get("ParentId")
                a_comments = comment_counter.get(answer_id, 0)
                row = [
                    site_alias, "", parent_id, "", "",
                    safe_date(answer_attrib.get("CreationDate", "")),
                    safe_date(answer_attrib.get("LastActivityDate", "")),
                    safe_date(answer_attrib.get("LastEditDate", "")),
                    answer_attrib.get("OwnerUserId", ""), answer_attrib.get("Score", "0"),
                    "", a_comments, "", answer_attrib.get("Body", ""),
                    site_file, answer_id, "answer"
                ]
                append_to_csv(row)
                site_answers_written += 1
            total_answers += site_answers_written

            # 5. Write comments to CSV
            site_comments_written = 0
            for comment_attrib in comments:
                post_id = comment_attrib.get("PostId")
                question_id = ""
                if post_id in relevant_question_ids:
                    question_id = post_id
                elif post_id in answer_id_to_question_id:
                    question_id = answer_id_to_question_id[post_id]
                else:
                    continue

                row = [
                    site_alias, "", question_id, "", "",
                    safe_date(comment_attrib.get("CreationDate", "")),
                    "", "", comment_attrib.get("UserId", ""),
                    comment_attrib.get("Score", "0"), "", "", "",
                    comment_attrib.get("Text", ""), site_file,
                    comment_attrib.get("Id", ""), "comment"
                ]
                append_to_csv(row)
                site_comments_written += 1
            total_comments_written += site_comments_written
            
            logger.info(f"[{site_alias}] Perguntas: {len(site_questions_df)}, Respostas: {site_answers_written}, Comentários: {site_comments_written}")

        except Exception as e:
            logger.error(f"[{site_alias}] ERRO ao processar arquivos do dump: {e}", exc_info=True)
        finally:
            shutil.rmtree(temp_dir)

    logger.info("\n##### RESUMO FINAL DA ETAPA 5 #####")
    logger.info(f"  - Total de Perguntas: {total_questions}")
    logger.info(f"  - Total de Respostas: {total_answers}")
    logger.info(f"  - Total de Comentários: {total_comments_written}")
    logger.info(f"Arquivo final salvo em: {CONNECTED_POSTS}")

def main():
    extract_posts_and_comments()

if __name__ == "__main__":
    main()
