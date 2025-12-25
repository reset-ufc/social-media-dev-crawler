import sys
import os
import subprocess
import csv
import pandas as pd
import xml.etree.ElementTree as ET
from utils_global import safe_date, get_logger
from paths import DUMP, CONNECTED_POSTS, RELEATED_POSTS, SITES

# Garante acesso aos módulos de diretórios superiores
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = get_logger(__name__)

POST_FEATURES = [
    "site_alias", "tags", "question_id", "accepted_answer_id", "answer_count",
    "creation_date", "last_activity_date", "last_edit_date",
    "owner_id", "score", "view_count", "comment_count",
    "title", "body", "site", "id", "type"
]

def write_csv_header():
    os.makedirs(os.path.dirname(CONNECTED_POSTS), exist_ok=True)
    with open(CONNECTED_POSTS, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(POST_FEATURES)

def append_batch_to_csv(batch):
    if not batch:
        return
    with open(CONNECTED_POSTS, "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(batch)

def get_relevant_questions():
    try:
        df = pd.read_csv(RELEATED_POSTS, dtype=str)
        if "question_id" not in df.columns and "id" in df.columns:
            df.rename(columns={"id": "question_id"}, inplace=True)
        return df
    except Exception as e:
        logger.error(f"Erro ao carregar perguntas relevantes: {e}")
        return pd.DataFrame()

def run_7z_stream(archive_path, filename):
    """Cria um processo subprocess para stream de um arquivo específico dentro do 7z."""
    cmd = ["7z", "e", archive_path, filename, "-so"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def extract_posts_and_comments():
    questions_df = get_relevant_questions()
    if questions_df.empty:
        logger.warning("Nenhuma pergunta relevante encontrada.")
        return

    write_csv_header()
    total_questions, total_answers, total_comments_written = 0, 0, 0

    for site_alias, site_file in SITES.items():
        logger.info(f"\n--- Processando site: {site_alias} (Zero-Disk Streaming) ---")
        archive_path = os.path.join(DUMP, site_file)
        if not os.path.exists(archive_path):
            continue

        site_questions_df = questions_df[questions_df["site_alias"] == site_alias]
        if site_questions_df.empty:
            continue

        relevant_question_ids = set(site_questions_df["question_id"].values)
        
        # Estruturas temporárias em memória para este site
        answers_to_write = []
        found_answer_ids = set()
        answer_id_to_question_id = {}
        comment_counter = {}
        comments_to_write = []

        try:
            # --- PASSO 1: Stream de Posts.xml (para encontrar Respostas) ---
            proc_posts = run_7z_stream(archive_path, "Posts.xml")
            context = ET.iterparse(proc_posts.stdout, events=("end",))
            for _, elem in context:
                if elem.tag == "row" and elem.attrib.get("PostTypeId") == "2":
                    parent_id = elem.attrib.get("ParentId")
                    if parent_id in relevant_question_ids:
                        answer_id = elem.attrib.get("Id")
                        found_answer_ids.add(answer_id)
                        answer_id_to_question_id[answer_id] = parent_id
                        
                        # Guardamos os dados da resposta
                        answers_to_write.append(elem.attrib)
                elem.clear()
            proc_posts.stdout.close()
            proc_posts.wait()

            # --- PASSO 2: Stream de Comments.xml (para encontrar Comentários) ---
            posts_to_track = relevant_question_ids.union(found_answer_ids)
            proc_comments = run_7z_stream(archive_path, "Comments.xml")
            context = ET.iterparse(proc_comments.stdout, events=("end",))
            for _, elem in context:
                if elem.tag == "row":
                    post_id = elem.attrib.get("PostId")
                    if post_id in posts_to_track:
                        comments_to_write.append(elem.attrib)
                        comment_counter[post_id] = comment_counter.get(post_id, 0) + 1
                elem.clear()
            proc_comments.stdout.close()
            proc_comments.wait()

            # --- PASSO 3: Escrita consolidada em Batch ---
            final_batch = []

            # Perguntas
            for _, q in site_questions_df.iterrows():
                qid = q["question_id"]
                final_batch.append([
                    site_alias, q.get("tags", ""), qid, q.get("accepted_answer_id", ""),
                    q.get("answer_count", "0"), q.get("creation_date", ""),
                    q.get("last_activity_date", ""), q.get("last_edit_date", ""),
                    q.get("owner_id", ""), q.get("score", "0"), q.get("view_count", "0"),
                    comment_counter.get(qid, 0), q.get("title", ""), q.get("body", ""),
                    q.get("site", ""), qid, "question"
                ])
                total_questions += 1

            # Respostas
            for a in answers_to_write:
                aid = a.get("Id")
                final_batch.append([
                    site_alias, "", a.get("ParentId"), "", "",
                    safe_date(a.get("CreationDate", "")), safe_date(a.get("LastActivityDate", "")),
                    safe_date(a.get("LastEditDate", "")), a.get("OwnerUserId", ""),
                    a.get("Score", "0"), "", comment_counter.get(aid, 0),
                    "", a.get("Body", ""), site_file, aid, "answer"
                ])
                total_answers += 1

            # Comentários
            for c in comments_to_write:
                pid = c.get("PostId")
                qid = pid if pid in relevant_question_ids else answer_id_to_question_id.get(pid)
                if qid:
                    final_batch.append([
                        site_alias, "", qid, "", "", safe_date(c.get("CreationDate", "")),
                        "", "", c.get("UserId", ""), c.get("Score", "0"),
                        "", "", "", c.get("Text", ""), site_file, c.get("Id", ""), "comment"
                    ])
                    total_comments_written += 1

            append_batch_to_csv(final_batch)
            logger.info(f"[{site_alias}] Sucesso. Batch gravado.")

        except Exception as e:
            logger.error(f"[{site_alias}] Falha no streaming: {e}")

    logger.info(f"\nRESUMO: Perguntas: {total_questions}, Respostas: {total_answers}, Comentários: {total_comments_written}")

def main():
    extract_posts_and_comments()

if __name__ == "__main__":
    main()