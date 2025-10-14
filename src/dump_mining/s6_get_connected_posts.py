import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import safe_date
from paths import BASE_DIR, CONNECTED_POSTS, RELEATED_POSTS, SITES
import csv
import pandas as pd
import xml.etree.ElementTree as ET
import tempfile
import py7zr
import shutil


# ==============================
# Configurações e constantes
# ==============================
POST_FEATURES = [
    "site_alias", "tags", "question_id", "accepted_answer_id", "answer_count",
    "creation_date", "last_activity_date", "last_edit_date",
    "owner_id", "score", "view_count", "comment_count",
    "title", "body", "site", "id", "type"
]

COMMENT_FEATURES = [
    "site_alias", "post_id", "comment_id", "user_id",
    "score", "creation_date", "text"
]


# ==============================
# Funções utilitárias
# ==============================
def get_relevant_questions():
    """Lê RELEATED_POSTS e retorna um conjunto de (site_alias, question_id)."""
    try:
        df = pd.read_csv(RELEATED_POSTS, dtype=str)
        if "local_id" not in df.columns:
            print("ERRO: coluna 'local_id' não encontrada em RELEATED_POSTS.")
            return set()
        return set(zip(df["site"], df["local_id"]))
    except Exception as e:
        print(f"Erro ao carregar perguntas relevantes: {e}")
        return set()


def write_csv_header(path, header):
    """Cria o CSV com cabeçalho se não existir."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(header)


def append_to_csv(path, row):
    """Adiciona uma linha ao CSV."""
    with open(path, "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(row)


# ==============================
# Parte 1: Conectar perguntas e respostas
# ==============================
def find_and_save_answers(relevant_questions):
    """Adiciona respostas correspondentes às perguntas filtradas."""
    if not relevant_questions:
        print("Nenhuma pergunta relevante encontrada.")
        return

    # adiciona as perguntas base ao arquivo CONNECTED_POSTS
    try:
        df_questions = pd.read_csv(RELEATED_POSTS, dtype=str)
        df_questions.rename(columns={"local_id": "id"}, inplace=True)
        df_questions["type"] = "question"
        df_questions["comment_count"] = "0"
        df_questions = df_questions.reindex(columns=POST_FEATURES)
        df_questions.to_csv(CONNECTED_POSTS, index=False, header=True)
        print(f"Perguntas adicionadas a: {CONNECTED_POSTS}")
    except Exception as e:
        print(f"ERRO ao carregar perguntas: {e}")
        return

    total_answers = 0

    for site_alias, site_file in SITES.items():
        archive_path = os.path.join(BASE_DIR, site_file)
        if not os.path.exists(archive_path):
            print(f"[{site_alias}] AVISO: .7z não encontrado.")
            continue

        print(f"[{site_alias}] Processando respostas em {archive_path}...")
        site_count = 0

        with py7zr.SevenZipFile(archive_path, "r") as archive:
            posts_files = [f for f in archive.getnames() if "Posts.xml" in f]
            if not posts_files:
                continue

            temp_dir = tempfile.mkdtemp()
            archive.extract(path=temp_dir, targets=posts_files)
            posts_path = os.path.join(temp_dir, posts_files[0])

            context = ET.iterparse(posts_path, events=("start",))
            for _, elem in context:
                if elem.tag != "row" or elem.attrib.get("PostTypeId") != "2":
                    continue

                parent_id = elem.attrib.get("ParentId")
                if (site_alias, parent_id) not in relevant_questions:
                    elem.clear()
                    continue

                post_id = elem.attrib.get("Id", "")
                row = [
                    site_alias, "", parent_id, "", "",  # tags, question_id, ...
                    safe_date(elem.attrib.get("CreationDate", "")),
                    safe_date(elem.attrib.get("LastActivityDate", "")),
                    safe_date(elem.attrib.get("LastEditDate", "")),
                    elem.attrib.get("OwnerUserId", ""),
                    elem.attrib.get("Score", "0"),
                    "", elem.attrib.get("CommentCount", "0"),
                    "", elem.attrib.get("Body", ""),
                    site_file, post_id, "answer"
                ]
                append_to_csv(CONNECTED_POSTS, row)
                site_count += 1
                elem.clear()

            shutil.rmtree(temp_dir)

        total_answers += site_count
        print(f"  → {site_count} respostas extraídas de {site_alias}")

    print(f"Total de respostas adicionadas: {total_answers}")


# ==============================
# Parte 2: Adicionar comentários
# ==============================
def find_and_save_comments():
    """Adiciona comentários de Comments.xml dos sites aos posts existentes."""
    try:
        df_posts = pd.read_csv(CONNECTED_POSTS, dtype=str)
    except FileNotFoundError:
        print(f"ERRO: {CONNECTED_POSTS} não encontrado.")
        return

    post_ids = set(df_posts["id"].astype(str))
    output_comments = CONNECTED_POSTS.replace(".csv", "_comments.csv")
    write_csv_header(output_comments, COMMENT_FEATURES)

    total_comments = 0
    for site_alias, site_file in SITES.items():
        archive_path = os.path.join(BASE_DIR, site_file)
        if not os.path.exists(archive_path):
            print(f"[{site_alias}] .7z não encontrado.")
            continue

        print(f"[{site_alias}] Extraindo comentários...")
        site_comments = 0

        with py7zr.SevenZipFile(archive_path, "r") as archive:
            comment_files = [f for f in archive.getnames() if "Comments.xml" in f]
            if not comment_files:
                continue

            temp_dir = tempfile.mkdtemp()
            archive.extract(path=temp_dir, targets=comment_files)
            comments_path = os.path.join(temp_dir, comment_files[0])

            context = ET.iterparse(comments_path, events=("start",))
            for _, elem in context:
                if elem.tag != "row":
                    continue
                post_id = elem.attrib.get("PostId")
                if post_id not in post_ids:
                    elem.clear()
                    continue

                row = [
                    site_alias,
                    post_id,
                    elem.attrib.get("Id", ""),
                    elem.attrib.get("UserId", ""),
                    elem.attrib.get("Score", "0"),
                    safe_date(elem.attrib.get("CreationDate", "")),
                    elem.attrib.get("Text", "").replace("\n", " ").strip()
                ]
                append_to_csv(output_comments, row)
                total_comments += 1
                site_comments += 1
                elem.clear()

            shutil.rmtree(temp_dir)

        print(f"  → {site_comments} comentários de {site_alias}")

    print(f"\nTotal de comentários extraídos: {total_comments}")
    print(f"Arquivo final salvo em: {output_comments}")


# ==============================
# Execução principal
# ==============================
def main():
    print("=== Etapa 6: Conectando Perguntas, Respostas e Comentários ===")
    relevant_questions = get_relevant_questions()
    find_and_save_answers(relevant_questions)
    find_and_save_comments()
    print("=== Etapa 6 Concluída com Sucesso ===")


if __name__ == "__main__":
    main()
