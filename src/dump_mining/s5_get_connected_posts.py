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

# Ordem padronizada de colunas (compatível com scripts 6 e 7)
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
        if "local_id" not in df.columns:
            df.rename(columns={"id": "local_id"}, inplace=True)
        return df
    except Exception as e:
        print(f"ERRO: Não foi possível carregar {RELEATED_POSTS}: {e}")
        return pd.DataFrame()


def extract_posts_and_comments():
    """Extrai perguntas, respostas e comentários para o arquivo CONNECTED_POSTS."""
    print("=== Etapa 5: Criando connected_posts.csv com comentários incluídos ===")

    questions_df = get_relevant_questions()
    if questions_df.empty:
        print("Nenhuma pergunta relevante encontrada.")
        return

    write_csv_header()

    total_questions = 0
    total_answers = 0
    total_comments = 0

    # 1️⃣ Adiciona as perguntas originais
    for _, q in questions_df.iterrows():
        row = [
            q.get("site", ""),
            q.get("tags", ""),
            q.get("local_id", ""),
            q.get("accepted_answer_id", ""),
            q.get("answer_count", "0"),
            q.get("creation_date", ""),
            q.get("last_activity_date", ""),
            q.get("last_edit_date", ""),
            q.get("owner_id", ""),
            q.get("score", "0"),
            q.get("view_count", "0"),
            q.get("comment_count", "0"),
            q.get("title", ""),
            q.get("body", ""),
            q.get("site", ""),
            q.get("local_id", ""),
            "question"
        ]
        append_to_csv(row)
        total_questions += 1

    # 2️⃣ Percorre os sites para encontrar respostas e comentários
    for site_alias, site_file in SITES.items():
        archive_path = os.path.join(BASE_DIR, site_file)
        if not os.path.exists(archive_path):
            print(f"[{site_alias}] Arquivo não encontrado: {archive_path}")
            continue

        print(f"[{site_alias}] Processando: {archive_path}")
        temp_dir = tempfile.mkdtemp()

        try:
            with py7zr.SevenZipFile(archive_path, mode="r") as archive:
                posts_files = [f for f in archive.getnames() if "Posts.xml" in f]
                comments_files = [f for f in archive.getnames() if "Comments.xml" in f]

                # Extrai Posts.xml e Comments.xml
                targets = posts_files + comments_files
                archive.extract(path=temp_dir, targets=targets)

                # 2.1️⃣ Respostas
                if posts_files:
                    posts_path = os.path.join(temp_dir, posts_files[0])
                    context = ET.iterparse(posts_path, events=("start",))
                    for _, elem in context:
                        if elem.tag != "row" or elem.attrib.get("PostTypeId") != "2":
                            continue
                        parent_id = elem.attrib.get("ParentId")
                        if parent_id not in questions_df["local_id"].values:
                            elem.clear()
                            continue

                        row = [
                            site_alias,
                            "",
                            parent_id,
                            "",
                            "",
                            safe_date(elem.attrib.get("CreationDate", "")),
                            safe_date(elem.attrib.get("LastActivityDate", "")),
                            safe_date(elem.attrib.get("LastEditDate", "")),
                            elem.attrib.get("OwnerUserId", ""),
                            elem.attrib.get("Score", "0"),
                            "",
                            elem.attrib.get("CommentCount", "0"),
                            "",
                            elem.attrib.get("Body", ""),
                            site_file,
                            elem.attrib.get("Id", ""),
                            "answer"
                        ]
                        append_to_csv(row)
                        total_answers += 1
                        elem.clear()

                # 2.2️⃣ Comentários
                if comments_files:
                    comments_path = os.path.join(temp_dir, comments_files[0])
                    context = ET.iterparse(comments_path, events=("start",))
                    for _, elem in context:
                        if elem.tag != "row":
                            continue
                        post_id = elem.attrib.get("PostId")
                        if post_id not in questions_df["local_id"].values:
                            elem.clear()
                            continue

                        row = [
                            site_alias,
                            "",
                            post_id,
                            "",
                            "",
                            safe_date(elem.attrib.get("CreationDate", "")),
                            "",
                            "",
                            elem.attrib.get("UserId", ""),
                            "",
                            "",
                            "",
                            "",
                            elem.attrib.get("Text", ""),
                            site_file,
                            elem.attrib.get("Id", ""),
                            "comment"
                        ]
                        append_to_csv(row)
                        total_comments += 1
                        elem.clear()

        except Exception as e:
            print(f"ERRO ao processar {site_alias}: {e}")
        finally:
            shutil.rmtree(temp_dir)

    # --- Atualizar o comment_count das perguntas e respostas ---
    try:
        print("\nAtualizando contagem de comentários em perguntas e respostas...")
        df = pd.read_csv(CONNECTED_POSTS, dtype=str)

        comment_counts = (
            df[df["type"] == "comment"]
            .groupby("question_id")
            .size()
            .reset_index(name="num_comments")
        )

        for _, row in comment_counts.iterrows():
            post_id = row["question_id"]
            num_comments = row["num_comments"]
            df.loc[
                (df["id"] == post_id) & (df["type"].isin(["question", "answer"])),
                "comment_count"
            ] = num_comments

        df.to_csv(CONNECTED_POSTS, index=False)
        print(f"✅ Contagem de comentários atualizada com sucesso ({len(comment_counts)} posts afetados).")
    except Exception as e:
        print(f"⚠️ Erro ao atualizar comment_count: {e}")

    print("\nResumo final:")
    print(f"  Perguntas adicionadas: {total_questions}")
    print(f"  Respostas adicionadas: {total_answers}")
    print(f"  Comentários adicionados: {total_comments}")
    print(f"Arquivo final consolidado salvo em: {CONNECTED_POSTS}")
    print("=== Etapa 5 Concluída ===")

def main():
    extract_posts_and_comments()


if __name__ == "__main__":
    main()
