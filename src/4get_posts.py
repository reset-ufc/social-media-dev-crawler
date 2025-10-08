import os
import csv
import pandas as pd
import xml.etree.ElementTree as ET
import datetime
import io
import py7zr
from config import *

POST_FEATURES = [
    'site', 'tags', 'question_id', 'accepted_answer_id', 'answer_count',
    'creation_date', 'last_activity_date', 'last_edit_date',
    'owner_id', 'score', 'view_count', 'title', 'body'
]

def safe_date(ts):
    """Converte uma data ISO em formato legível."""
    try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
        return dt.strftime('%Y/%m/%d, %H:%M:%S')
    except (ValueError, TypeError):
        return ts

def get_related_tags():
    """Lê as tags relacionadas do arquivo CSV gerado nas heurísticas."""
    try:
        df = pd.read_csv(RELEATED_TAGS)
        return set(df['tag'])
    except FileNotFoundError:
        print(f"ERRO: Arquivo de tags relacionadas não encontrado: {RELEATED_TAGS}")
        return set()

def initialize_csv(path):
    """Cria o CSV com cabeçalho, se ainda não existir."""
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(POST_FEATURES)

def has_answers_or_comments(post_id, site_name):
    """
    Verifica se o post tem respostas ou comentários
    dentro dos arquivos compactados .7z.
    """
    base_path = os.path.join(BASE_DIR, f"{site_name}.7z")

    # Verifica comentários
    with py7zr.SevenZipFile(base_path, mode='r') as archive:
        for file in archive.getnames():
            if "Comments.xml" in file:
                with archive.read([file])[file] as f:
                    for line in io.TextIOWrapper(f, encoding="utf-8", errors="ignore"):
                        if f'PostId="{post_id}"' in line:
                            return True  # Encontrou comentário

            if "Posts.xml" in file:  # Verifica respostas
                with archive.read([file])[file] as f:
                    for line in io.TextIOWrapper(f, encoding="utf-8", errors="ignore"):
                        if f'ParentId="{post_id}"' in line:
                            return True  # Encontrou resposta
    return False

def find_and_save_related_posts(related_tags):
    """Procura e salva posts que tenham as tags relacionadas e pelo menos uma resposta/comentário."""
    if not related_tags:
        print("Nenhuma tag relacionada para processar.")
        return

    processed_posts = set()
    site_post_counts = {}

    initialize_csv(RELEATED_POSTS)

    for site_alias, site_name in SITES.items():
        site_archive = os.path.join(BASE_DIR, f"{site_name}.7z")
        site_csv = f"related_posts_{site_alias}.csv"
        initialize_csv(site_csv)
        site_count = 0

        if not os.path.exists(site_archive):
            print(f"AVISO: Arquivo compactado não encontrado para '{site_alias}' em: {site_archive}")
            continue

        print(f" Processando: {site_archive}")

        with py7zr.SevenZipFile(site_archive, mode='r') as archive:
            for file in archive.getnames():
                if not file.endswith("Posts.xml"):
                    continue

                with archive.read([file])[file] as f:
                    context = ET.iterparse(io.TextIOWrapper(f, encoding="utf-8", errors="ignore"), events=("start",))
                    for _, elem in context:
                        if elem.tag == "row":
                            post_id = elem.attrib.get("Id")
                            if post_id in processed_posts:
                                elem.clear()
                                continue

                            tags_field = elem.attrib.get("Tags", "")
                            if tags_field:
                                post_tags = set(tags_field.strip('|').split('|'))
                                if not related_tags.isdisjoint(post_tags):
                                    # Só inclui posts com respostas/comentários
                                    if not has_answers_or_comments(post_id, site_name):
                                        elem.clear()
                                        continue

                                    row = [
                                        site_alias,
                                        ";".join(post_tags),
                                        post_id,
                                        elem.attrib.get("AcceptedAnswerId", ""),
                                        elem.attrib.get("AnswerCount", "0"),
                                        safe_date(elem.attrib.get("CreationDate", "")),
                                        safe_date(elem.attrib.get("LastActivityDate", "")),
                                        safe_date(elem.attrib.get("LastEditDate", "")),
                                        elem.attrib.get("OwnerUserId", ""),
                                        elem.attrib.get("Score", "0"),
                                        elem.attrib.get("ViewCount", "0"),
                                        elem.attrib.get("Title", ""),
                                        elem.attrib.get("Body", "")
                                    ]

                                    with open(RELEATED_POSTS, "a", encoding="utf-8", newline="") as f_csv:
                                        csv.writer(f_csv).writerow(row)
                                    with open(site_csv, "a", encoding="utf-8", newline="") as f_site:
                                        csv.writer(f_site).writerow(row)

                                    processed_posts.add(post_id)
                                    site_count += 1

                            elem.clear()

        site_post_counts[site_alias] = site_count
        print(f"→ {site_alias}: {site_count} posts encontrados ")

    print("\nResumo final:")
    for site, count in site_post_counts.items():
        print(f"  - {site}: {count} posts válidos")

    with open("site_post_counts.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["site", "total_posts"])
        for site, count in site_post_counts.items():
            writer.writerow([site, count])

    print("\n Arquivo 'site_post_counts.csv' salvo com sucesso!")

if __name__ == "__main__":
    print("Inicializando coleta dentro dos arquivos compactados...")
    tags_to_find = get_related_tags()
    print("Buscando posts relacionados com respostas/comentários...")
    find_and_save_related_posts(tags_to_find)
    print("Processamento concluído!")
