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

# Colunas padronizadas com o pipeline (agora com CommentCount)
POST_FEATURES = [
    "site_alias", "tags", "question_id", "accepted_answer_id", "answer_count",
    "creation_date", "last_activity_date", "last_edit_date",
    "owner_id", "score", "view_count", "comment_count",
    "title", "body", "site", "id", "type"
]


def get_relevant_questions():
    """
    Lê o arquivo RELEATED_POSTS e retorna um conjunto de (site, local_id)
    para busca eficiente das respostas correspondentes.
    """
    try:
        df = pd.read_csv(RELEATED_POSTS, dtype=str)
        if 'local_id' not in df.columns:
            print("ERRO: Coluna 'local_id' não encontrada em RELEATED_POSTS.")
            return set()
        return set(zip(df['site'], df['local_id']))
    except FileNotFoundError:
        print(f"ERRO: Arquivo não encontrado: {RELEATED_POSTS}")
        return set()
    except Exception as e:
        print(f"Erro ao carregar RELEATED_POSTS: {e}")
        return set()


def write_csv_header():
    """Cria o arquivo CONNECTED_POSTS com cabeçalho."""
    os.makedirs(os.path.dirname(CONNECTED_POSTS), exist_ok=True)
    with open(CONNECTED_POSTS, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(POST_FEATURES)


def append_to_csv(row):
    """Adiciona uma linha ao CSV de posts conectados."""
    with open(CONNECTED_POSTS, "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(row)


def find_and_save_answers(relevant_questions):
    """
    Localiza e adiciona respostas (PostTypeId=2) às perguntas relevantes.
    Também mantém os posts originais e adiciona coluna 'comment_count'.
    """
    if not relevant_questions:
        print("Nenhuma pergunta relevante encontrada.")
        return

    print(f"Lendo perguntas originais de: {RELEATED_POSTS}")
    try:
        df_questions = pd.read_csv(RELEATED_POSTS, dtype=str)
        df_questions.rename(columns={"local_id": "id"}, inplace=True)
        df_questions["type"] = "question"
        df_questions["comment_count"] = "0"  # Inicializa
        df_questions = df_questions.reindex(columns=POST_FEATURES)
        df_questions.to_csv(CONNECTED_POSTS, index=False, header=True)
        print("Perguntas base adicionadas ao arquivo CONNECTED_POSTS.")
    except Exception as e:
        print(f"ERRO ao carregar perguntas de {RELEATED_POSTS}: {e}")
        return

    total_answers_found = 0

    # Itera pelos sites e extrai respostas
    for site_alias, site_file in SITES.items():
        archive_path = os.path.join(BASE_DIR, site_file)
        if not os.path.exists(archive_path):
            print(f"AVISO: Arquivo não encontrado: {archive_path}")
            continue

        print(f"[{site_alias}] Processando: {archive_path}")
        site_answers_count = 0

        with py7zr.SevenZipFile(archive_path, mode="r") as archive:
            posts_files = [f for f in archive.getnames() if "Posts.xml" in f]
            if not posts_files:
                print(f"[{site_alias}] Nenhum Posts.xml encontrado.")
                continue

            temp_dir = tempfile.mkdtemp()
            archive.extract(path=temp_dir, targets=posts_files)
            posts_path = os.path.join(temp_dir, posts_files[0])

            try:
                context = ET.iterparse(posts_path, events=("start",))
                for _, elem in context:
                    if elem.tag != "row" or elem.attrib.get("PostTypeId") != "2":
                        continue

                    parent_id = elem.attrib.get("ParentId")
                    if (site_file, parent_id) not in relevant_questions:
                        elem.clear()
                        continue

                    post_id = elem.attrib.get("Id", "")
                    row = [
                        site_alias,  # site_alias
                        "",  # tags
                        parent_id,  # question_id
                        "",  # accepted_answer_id
                        "",  # answer_count
                        safe_date(elem.attrib.get("CreationDate", "")),
                        safe_date(elem.attrib.get("LastActivityDate", "")),
                        safe_date(elem.attrib.get("LastEditDate", "")),
                        elem.attrib.get("OwnerUserId", ""),
                        elem.attrib.get("Score", "0"),
                        "",  # view_count
                        elem.attrib.get("CommentCount", "0"),  # 👈 novo campo
                        "",  # title
                        elem.attrib.get("Body", ""),
                        site_file,  # site
                        post_id,  # id
                        "answer",  # type
                    ]
                    append_to_csv(row)
                    site_answers_count += 1
                    elem.clear()
            finally:
                shutil.rmtree(temp_dir)

        total_answers_found += site_answers_count
        print(f"  → {site_answers_count} respostas extraídas de {site_alias}")

    print(f"\nTotal de respostas adicionadas: {total_answers_found}")
    print(f"Arquivo final consolidado salvo em: {CONNECTED_POSTS}")


def main():
    print("=== Iniciando Etapa 6: Conectando Perguntas e Respostas ===")
    relevant_questions = get_relevant_questions()
    find_and_save_answers(relevant_questions)
    print("=== Etapa 6 Concluída com Sucesso ===")


if __name__ == "__main__":
    main()
