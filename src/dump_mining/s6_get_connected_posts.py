import shutil
import py7zr
import tempfile
import xml.etree.ElementTree as ET
import pandas as pd
import csv

from pathlib import Path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import *
from utils import safe_date


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
def get_relevant_questions(input_path: Path):
    """Lê o arquivo de entrada e retorna um conjunto de (site_alias, question_id)."""
    try:
        df = pd.read_csv(input_path, dtype=str)
        if "local_id" not in df.columns:
            print(f"ERRO: coluna 'local_id' não encontrada em {input_path}.")
            return set()
        return set(zip(df["site_alias"], df["local_id"]))
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
def find_and_save_answers(relevant_questions, input_path: Path):
    """Adiciona respostas correspondentes às perguntas filtradas."""
    if not relevant_questions:
        print("Nenhuma pergunta relevante encontrada.")
        return

    # adiciona as perguntas base ao arquivo CONNECTED_POSTS
    try:
        df_questions = pd.read_csv(input_path, dtype=str)
        df_questions.rename(columns={"local_id": "id"}, inplace=True)
        df_questions["type"] = "post"
        df_questions["comment_count"] = "0"
        df_questions = df_questions.reindex(columns=POST_FEATURES)
        df_questions.to_csv(CONNECTED_POSTS, index=False)
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
                    # tags, question_id, ...
                    site_alias, "", parent_id, "", "",
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
# Parte 2: Filtrar posts com auto-resposta única
# ==============================
def filter_self_answered_posts():
    """
    Remove perguntas que têm apenas uma resposta e essa resposta é do mesmo autor.
    """
    print("\nFiltrando posts com uma única auto-resposta...")
    try:
        df = pd.read_csv(CONNECTED_POSTS, dtype=str)
    except FileNotFoundError:
        print(
            f"ERRO: Arquivo {CONNECTED_POSTS} não encontrado para filtragem.")
        return

    questions = df[df['type'] == 'post'].set_index('id')
    answers = df[df['type'] == 'answer']

    # Conta o número de respostas por pergunta
    answer_counts = answers.groupby('question_id').size()

    # Identifica perguntas com apenas 1 resposta
    single_answer_qids = answer_counts[answer_counts == 1].index

    # Filtra as respostas que pertencem a essas perguntas
    single_answers = answers[answers['question_id'].isin(single_answer_qids)]

    # Compara o owner_id da pergunta e da resposta
    q_owner_ids = questions.loc[single_answers['question_id']
                                ]['owner_id'].values
    a_owner_ids = single_answers['owner_id'].values
    self_answered_qids = single_answers[q_owner_ids ==
                                        a_owner_ids]['question_id'].unique()

    # Remove as perguntas e suas respectivas respostas
    initial_count = len(df)
    df_filtered = df[~df['question_id'].isin(self_answered_qids)]
    df_filtered.to_csv(CONNECTED_POSTS, index=False)
    print(
        f"Removidos {len(self_answered_qids)} posts (e suas respostas) por terem uma única auto-resposta.")

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
            comment_files = [
                f for f in archive.getnames() if "Comments.xml" in f]
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
    relevant_questions = get_relevant_questions(FILTRED_POSTS)
    find_and_save_answers(relevant_questions, FILTRED_POSTS)
    filter_self_answered_posts()
    # find_and_save_comments() # Comentado para focar na lógica de posts
    print("=== Etapa 6 Concluída com Sucesso ===")


if __name__ == "__main__":
    main()
