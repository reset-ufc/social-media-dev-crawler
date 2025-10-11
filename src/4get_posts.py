import os
import csv
import pandas as pd
import xml.etree.ElementTree as ET
import io
import py7zr
import re
from config import *

# --- Configurações ---
POSTS_OUTPUT = os.path.join(DATA, "coarse", "final_posts.csv")


POST_FEATURES = [
    "site", "tags", "question_id", "accepted_answer_id", "answer_count",
    "creation_date", "last_activity_date", "last_edit_date",
    "owner_id", "score", "view_count", "title", "body"
]
os.makedirs(os.path.dirname(RELEATED_POSTS), exist_ok=True)

# --- Utils ---------------------------------------------------------
def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

def safe_date(value):
    """Retorna a data como string legível, mesmo se o formato estiver estranho."""
    return value[:19].replace("T", " ") if isinstance(value, str) else ""

def extract_tag_list(tags_field):
    """Normaliza tags em formato semântico (python;crypto)."""
    if not tags_field:
        return ""
    if '<' in tags_field and '>' in tags_field:
        tags = [t.strip() for t in re.findall(r'<(.+?)>', tags_field)]
    else:
        tags = [t.strip() for t in re.split(r'[\s,;|]+', tags_field) if t.strip()]
    return ";".join(tags)

# --- Funções principais --------------------------------------------
def initialize_csv(path):
    """Cria o CSV com cabeçalho se não existir."""
    if not os.path.exists(path):
        ensure_parent_dir(path)
        with open(path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(POST_FEATURES)

def extract_post_data(elem, site_alias):
    """Extrai os atributos relevantes de uma entrada <row>."""
    tags_field = elem.attrib.get("Tags", "")
    return [
        site_alias,
        extract_tag_list(tags_field),
        elem.attrib.get("Id", ""),
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

def get_related_post_ids():
    """Lê os IDs de posts do arquivo RELEATED_POSTS."""
    if not os.path.exists(RELEATED_POSTS):
        print(f"ERRO: {RELEATED_POSTS} não encontrado. Rode o script anterior primeiro.")
        return {}

    df = pd.read_csv(RELEATED_POSTS, dtype=str)
    grouped = df.groupby("site")["question_id"].apply(set).to_dict()
    print(f"Sites carregados: {list(grouped.keys())}")
    return grouped

def extract_posts_from_archives():
    """Extrai os posts completos de acordo com os IDs de interesse."""
    site_post_ids = get_related_post_ids()
    if not site_post_ids:
        return

    initialize_csv(POSTS_OUTPUT)

    site_post_counts = {}

    for site_alias, site_name in SITES.items():
        if site_alias not in site_post_ids:
            continue

        ids_to_find = site_post_ids[site_alias]
        archive_path = os.path.join(BASE_DIR, site_name)

        if not os.path.exists(archive_path):
            print(f"AVISO: {archive_path} não encontrado.")
            continue

        print(f"[{site_alias}] Extraindo posts ({len(ids_to_find)} IDs) de {archive_path}...")

        count = 0
        with py7zr.SevenZipFile(archive_path, mode="r") as archive:
            post_files = [f for f in archive.getnames() if f.endswith("Posts.xml")]
            if not post_files:
                print(f"  Nenhum Posts.xml encontrado em {archive_path}")
                continue

            with archive.read([post_files[0]])[post_files[0]] as f:
                context = ET.iterparse(io.TextIOWrapper(f, encoding="utf-8", errors="ignore"), events=("start",))
                with open(POSTS_OUTPUT, "a", encoding="utf-8", newline="") as out_csv:
                    writer = csv.writer(out_csv)
                    for _, elem in context:
                        if elem.tag != "row":
                            continue
                        post_id = elem.attrib.get("Id")
                        if post_id in ids_to_find:
                            writer.writerow(extract_post_data(elem, site_alias))
                            count += 1
                            ids_to_find.remove(post_id)
                        elem.clear()

        site_post_counts[site_alias] = count
        print(f"  → {site_alias}: {count} posts extraídos")

    # --- resumo final ---
    print("\nResumo final:")
    total = 0
    for site, count in site_post_counts.items():
        print(f"  - {site}: {count} posts válidos")
        total += count
    print(f"\n Total geral: {total} posts extraídos")
    print(f"Arquivo consolidado salvo em: {POSTS_OUTPUT}")

    # salva contagem por site
    counts_csv = os.path.join(DATA, "coarse", "post_counts.csv")
    with open(counts_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["site", "total_posts"])
        for site, count in site_post_counts.items():
            writer.writerow([site, count])
        writer.writerow(["TOTAL", total])
    print(f"Arquivo 'post_counts.csv' salvo em: {counts_csv}")

# --- Execução principal ---
if __name__ == "__main__":
    print("Iniciando 4get_posts.py ...")
    extract_posts_from_archives()
    print("Processamento concluído com sucesso!")
