import os
import csv
import pandas as pd
import xml.etree.ElementTree as ET
import io
import py7zr
import shutil
from config import *

# Colunas para os posts, consistente com 4get_posts.py
POST_FEATURES = [
    'site_alias', 'tags', 'question_id', 'accepted_answer_id', 'answer_count',
    'creation_date', 'last_activity_date', 'last_edit_date',
    'owner_id', 'score', 'view_count', 'title', 'body',
    'local_id', 'site'
]


def get_relevant_questions():
    """
    Lê o arquivo RELEATED_POSTS e retorna um conjunto de tuplas (site, local_id)
    para uma busca eficiente.
    """
    try:
        df = pd.read_csv(RELEATED_POSTS)
        # Usamos 'site' (nome completo) e 'local_id' (ID da pergunta)
        return set(zip(df['site'], df['local_id'].astype(str)))
    except FileNotFoundError:
        print(
            f"ERRO: Arquivo de posts relacionados não encontrado: {RELEATED_POSTS}")
        return set()


def find_and_save_answers(relevant_questions):
    """
    Encontra e salva as respostas (PostTypeId="2") para as perguntas relevantes.
    """
    if not relevant_questions:
        print("Nenhuma pergunta relevante para processar.")
        return

    # 1. Copia os posts originais para o novo arquivo
    print(
        f"Copiando posts originais de {RELEATED_POSTS} para {CONNECTED_POSTS}...")
    try:
        shutil.copy(RELEATED_POSTS, CONNECTED_POSTS)
        print("Cópia concluída com sucesso.")
    except FileNotFoundError:
        print(f"ERRO: Arquivo de origem {RELEATED_POSTS} não encontrado.")
        return

    total_answers_found = 0

    # 2. Itera sobre os arquivos .7z para encontrar as respostas
    for site_alias, site_name in SITES.items():
        site_archive = os.path.join(BASE_DIR, f"{site_name}.7z")

        if not os.path.exists(site_archive):
            print(
                f"AVISO: Arquivo compactado não encontrado para '{site_alias}': {site_archive}")
            continue

        print(f"Processando respostas em: {site_archive}")
        site_answers_count = 0

        with py7zr.SevenZipFile(site_archive, mode='r') as archive:
            # Assumimos que há apenas um Posts.xml por site
            posts_xml_path = "Posts.xml"
            if posts_xml_path not in archive.getnames():
                continue

            with archive.read([posts_xml_path])[posts_xml_path] as f:
                context = ET.iterparse(io.TextIOWrapper(
                    f, encoding="utf-8", errors="ignore"), events=("start",))
                for _, elem in context:
                    if elem.tag == "row":
                        post_type = elem.attrib.get("PostTypeId")
                        # Verifica se é uma resposta
                        if post_type == "2":
                            parent_id = elem.attrib.get("ParentId")
                            # Verifica se a resposta pertence a uma pergunta relevante
                            if (site_name, parent_id) in relevant_questions:
                                post_id = elem.attrib.get("Id")
                                row = [
                                    site_alias, "",  # tags
                                    parent_id,  # question_id
                                    # accepted_answer_id, answer_count, etc.
                                    "", "", "", "", "",
                                    elem.attrib.get("OwnerUserId", ""),
                                    elem.attrib.get("Score", "0"),
                                    "",  # view_count
                                    "",  # title
                                    elem.attrib.get("Body", ""),
                                    post_id,  # local_id
                                    site_name
                                ]

                                with open(CONNECTED_POSTS, "a", encoding="utf-8", newline="") as f_csv:
                                    csv.writer(f_csv).writerow(row)

                                site_answers_count += 1
                        elem.clear()

        total_answers_found += site_answers_count
        print(
            f"  → {site_answers_count} respostas encontradas para {site_alias}.")

    print(f"\nTotal de respostas adicionadas: {total_answers_found}")
    print(f"Arquivo final salvo em: {CONNECTED_POSTS}")


if __name__ == "__main__":
    print("Iniciando a busca por posts conectados (respostas)...")

    # Pega as perguntas que já foram filtradas como relevantes
    questions_to_find_answers_for = get_relevant_questions()

    # Busca as respostas para essas perguntas e as adiciona ao novo arquivo
    find_and_save_answers(questions_to_find_answers_for)

    print("\nProcessamento de posts conectados concluído!")
