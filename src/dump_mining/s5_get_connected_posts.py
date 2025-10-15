import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import safe_date
from paths import BASE_DIR, CONNECTED_POSTS, CONNECTED_COMMENTS, RELEATED_POSTS, SITES
import csv
import pandas as pd
import xml.etree.ElementTree as ET
import tempfile
import py7zr
import shutil


POST_FEATURES = [
    "site_alias", "tags", "question_id", "accepted_answer_id", "answer_count",
    "comment_count", "favorite_count",
    "creation_date", "last_activity_date", "last_edit_date",
    "owner_id", "score", "view_count",
    "title", "body", "site", "id", "type"
]

COMMENT_FEATURES = [
    "site_alias", "post_id", "comment_id", "creation_date",
    "score", "text", "user_id"
]


def get_relevant_questions():
    """Lê perguntas relevantes de RELEATED_POSTS."""
    try:
        df = pd.read_csv(RELEATED_POSTS, dtype=str)
        if 'local_id' not in df.columns:
            df.rename(columns={'question_id': 'local_id'}, inplace=True)
        return set(zip(df['site'], df['local_id']))
    except Exception as e:
        print(f"Erro ao carregar RELEATED_POSTS: {e}")
        return set()


def append_csv(path, header, rows):
    """Escreve ou adiciona dados a um CSV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file_exists = os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerows(rows)


def find_posts_and_comments(relevant_questions):
    """Extrai perguntas, respostas e comentários."""
    all_comments = []
    all_posts = []

    for site_alias, site_file in SITES.items():
        archive_path = os.path.join(BASE_DIR, site_file)
        if not os.path.exists(archive_path):
            print(f"AVISO: {archive_path} não encontrado.")
            continue

        print(f"[{site_alias}] Processando {archive_path} ...")

        with py7zr.SevenZipFile(archive_path, mode="r") as archive:
            files = archive.getnames()
            posts_xml = next((f for f in files if "Posts.xml" in f), None)
            comments_xml = next((f for f in files if "Comments.xml" in f), None)
            if not posts_xml:
                continue

            temp_dir = tempfile.mkdtemp()
            try:
                archive.extract(path=temp_dir, targets=[f for f in [posts_xml, comments_xml] if f])
                posts_path = os.path.join(temp_dir, posts_xml)
                comments_path = os.path.join(temp_dir, comments_xml) if comments_xml else None

                # --- Processa Posts.xml (perguntas e respostas) ---
                context = ET.iterparse(posts_path, events=("start",))
                for _, elem in context:
                    if elem.tag != "row":
                        continue

                    post_type = elem.attrib.get("PostTypeId")
                    post_id = elem.attrib.get("Id", "")
                    parent_id = elem.attrib.get("ParentId")

                    if post_type == "1":  # pergunta
                        row_type = "question"
                        question_id = post_id
                    elif post_type == "2":  # resposta
                        row_type = "answer"
                        question_id = parent_id
                    else:
                        continue

                    row = [
                        site_alias,
                        elem.attrib.get("Tags", ""),
                        question_id,
                        elem.attrib.get("AcceptedAnswerId", ""),
                        elem.attrib.get("AnswerCount", "0"),
                        elem.attrib.get("CommentCount", "0"),
                        elem.attrib.get("FavoriteCount", "0"),
                        safe_date(elem.attrib.get("CreationDate", "")),
                        safe_date(elem.attrib.get("LastActivityDate", "")),
                        safe_date(elem.attrib.get("LastEditDate", "")),
                        elem.attrib.get("OwnerUserId", ""),
                        elem.attrib.get("Score", "0"),
                        elem.attrib.get("ViewCount", "0"),
                        elem.attrib.get("Title", ""),
                        elem.attrib.get("Body", ""),
                        site_file,
                        post_id,
                        row_type
                    ]
                    all_posts.append(row)
                    elem.clear()

                # --- Processa Comments.xml ---
                if comments_path and os.path.exists(comments_path):
                    context = ET.iterparse(comments_path, events=("start",))
                    for _, elem in context:
                        if elem.tag != "row":
                            continue
                        post_id = elem.attrib.get("PostId")
                        comment_row = [
                            site_alias,
                            post_id,
                            elem.attrib.get("Id", ""),
                            safe_date(elem.attrib.get("CreationDate", "")),
                            elem.attrib.get("Score", "0"),
                            elem.attrib.get("Text", ""),
                            elem.attrib.get("UserId", "")
                        ]
                        all_comments.append(comment_row)
                        elem.clear()

            finally:
                shutil.rmtree(temp_dir)

    append_csv(CONNECTED_POSTS, POST_FEATURES, all_posts)
    append_csv(CONNECTED_COMMENTS, COMMENT_FEATURES, all_comments)

    print(f"\n[OK] Total de posts: {len(all_posts)}, comentários: {len(all_comments)}")
    print(f"→ {CONNECTED_POSTS}")
    print(f"→ {CONNECTED_COMMENTS}")


def main():
    print("=== Etapa 5: Conectando perguntas, respostas e comentários ===")
    relevant = get_relevant_questions()
    find_posts_and_comments(relevant)
    print("=== Etapa 5 concluída ===")


if __name__ == "__main__":
    main()
