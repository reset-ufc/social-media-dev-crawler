import os
import csv
import pandas as pd
import xml.etree.ElementTree as ET
import py7zr
import tempfile
import shutil
import re
from config import *

# --- Utils ---------------------------------------------------------
def extract_tag_list(tags_field):
    """Extrai tags em qualquer formato comum (<tag> ou separadas por ; | espaço)."""
    if not isinstance(tags_field, str) or tags_field.strip() == "":
        return []
    if '<' in tags_field and '>' in tags_field:
        return re.findall(r'<(.+?)>', tags_field)
    if ';' in tags_field:
        return [t.strip() for t in tags_field.split(';') if t.strip()]
    if '|' in tags_field:
        return [t.strip() for t in tags_field.split('|') if t.strip()]
    return [t.strip() for t in re.split(r'[\s,;|]+', tags_field) if t.strip()]

def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

# --- Calcula C -----------------------------------------------------
def calculate_c():
    """Calcula c = número total de perguntas (PostTypeId=1) que contêm QUESTION_TAG nos dumps compactados (.7z)."""
    print("Calculando a constante 'c' ...")
    c = 0

    for site_alias, site_file in SITES.items():
        archive_path = os.path.join(BASE_DIR, site_file)
        if not os.path.exists(archive_path):
            print(f"[{site_alias}] Arquivo .7z não encontrado em: {archive_path}")
            continue

        try:
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                posts_files = [f for f in archive.getnames() if "Posts.xml" in f]
                if not posts_files:
                    continue

                temp_dir = tempfile.mkdtemp()
                archive.extract(path=temp_dir, targets=posts_files)
                posts_path = os.path.join(temp_dir, posts_files[0])

                context = ET.iterparse(posts_path, events=("start",))
                for _, elem in context:
                    if elem.tag == "row" and elem.attrib.get("PostTypeId") == "1":
                        tags_field = elem.attrib.get("Tags", "")
                        tags = extract_tag_list(tags_field)
                        if QUESTION_TAG in tags:
                            c += 1
                    elem.clear()

                shutil.rmtree(temp_dir)

        except Exception as e:
            print(f"[{site_alias}] Erro ao processar: {e}")

    print(f"Constante c = {c}")
    return c

# --- Calcula H2 ----------------------------------------------------
def calculate_h2():
    """Calcula h2 = a / c e grava no arquivo de tags relacionadas."""
    print("Calculando h2 ...")

    coarse_tags_path = os.path.join(DATA, "releated_tags.csv")
    if not os.path.exists(coarse_tags_path):
        print(f"ERRO: {coarse_tags_path} não encontrado. Rode H1 primeiro.")
        return set()

    df = pd.read_csv(coarse_tags_path)
    if 'a' not in df.columns:
        print("ERRO: coluna 'a' não encontrada. Rode make_releated_tags() primeiro.")
        return set()

    df['a'] = pd.to_numeric(df['a'], errors='coerce').fillna(0).astype(int)
    c = calculate_c()
    if c <= 0:
        print("ERRO: valor de c = 0. Não é possível calcular h2.")
        return set()

    df['h2'] = (df['a'] / c).fillna(0)
    df = df[df['h2'] >= THRE2].reset_index(drop=True)

    df.to_csv(coarse_tags_path, index=False, encoding='utf-8')
    print(f"Coluna 'h2' adicionada e arquivo atualizado: {coarse_tags_path}")

    tags = set(df['tag'])
    print(f"Total de tags relacionadas válidas: {len(tags)}")
    return tags

# --- Extrai posts relacionados -------------------------------------
def find_related_posts(valid_tags):
    """Procura posts com as tags relacionadas e salva por site e geral."""
    if not valid_tags:
        print("Nenhuma tag válida para buscar.")
        return

    coarse_dir = os.path.join(DATA, "coarse")
    ensure_parent_dir(coarse_dir)

    related_posts_path = os.path.join(coarse_dir, "releated_posts.csv")
    ensure_parent_dir(related_posts_path)

    header = [
        "site", "tags", "question_id", "accepted_answer_id", "answer_count",
        "creation_date", "last_activity_date", "last_edit_date",
        "owner_id", "score", "view_count", "title", "body"
    ]
    if not os.path.exists(related_posts_path):
        with open(related_posts_path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(header)

    site_counts = {}

    for site_alias, site_file in SITES.items():
        archive_path = os.path.join(BASE_DIR, site_file)
        site_csv = os.path.join(coarse_dir, f"releated_posts_{site_alias}.csv")

        if not os.path.exists(archive_path):
            print(f"[{site_alias}] Arquivo não encontrado: {archive_path}")
            continue

        print(f"[{site_alias}] Processando {archive_path} ...")
        count = 0

        with py7zr.SevenZipFile(archive_path, mode="r") as archive:
            posts_files = [f for f in archive.getnames() if "Posts.xml" in f]
            if not posts_files:
                print(f"  Nenhum Posts.xml encontrado.")
                continue

            temp_dir = tempfile.mkdtemp()
            archive.extract(path=temp_dir, targets=posts_files)
            posts_path = os.path.join(temp_dir, posts_files[0])

            with open(related_posts_path, "a", encoding="utf-8", newline="") as f_all, \
                 open(site_csv, "w", encoding="utf-8", newline="") as f_site:

                writer_all = csv.writer(f_all)
                writer_site = csv.writer(f_site)
                writer_site.writerow(header)

                context = ET.iterparse(posts_path, events=("start",))
                for _, elem in context:
                    if elem.tag == "row" and elem.attrib.get("PostTypeId") == "1":
                        tags_field = elem.attrib.get("Tags", "")
                        tags = set(extract_tag_list(tags_field))
                        if tags and not valid_tags.isdisjoint(tags):
                            row = [
                                site_alias,
                                ";".join(tags),
                                elem.attrib.get("Id", ""),
                                elem.attrib.get("AcceptedAnswerId", ""),
                                elem.attrib.get("AnswerCount", "0"),
                                elem.attrib.get("CreationDate", ""),
                                elem.attrib.get("LastActivityDate", ""),
                                elem.attrib.get("LastEditDate", ""),
                                elem.attrib.get("OwnerUserId", ""),
                                elem.attrib.get("Score", "0"),
                                elem.attrib.get("ViewCount", "0"),
                                elem.attrib.get("Title", ""),
                                elem.attrib.get("Body", "")
                            ]
                            writer_all.writerow(row)
                            writer_site.writerow(row)
                            count += 1
                    elem.clear()

            shutil.rmtree(temp_dir)
        site_counts[site_alias] = count
        print(f"  → {site_alias}: {count} posts encontrados")

    print("\nResumo final:")
    for s, c in site_counts.items():
        print(f"  - {s}: {c} posts válidos")

# --- MAIN ----------------------------------------------------------
if __name__ == "__main__":
    print("Iniciando 3get_related_posts.py ...")
    valid_tags = calculate_h2()
    find_related_posts(valid_tags)
    print("Processo da Heurística 2 (com geração de posts relacionados) finalizado com sucesso!")
