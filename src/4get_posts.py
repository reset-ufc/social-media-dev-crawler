import os
import csv
import pandas as pd
import xml.etree.ElementTree as ET
<<<<<<< HEAD
import datetime
import re
import py7zr
import tempfile
import shutil
=======
import io
import py7zr
import re
>>>>>>> ac736632fc5c62e2503c0771d5f26234978aaa44
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

<<<<<<< HEAD
def preload_commented_and_answered_posts(site_archive_path):
    """
    Lê os arquivos Comments.xml e Posts.xml uma vez para extrair todos os IDs
    de posts que têm comentários ou são respostas. Isso evita reabrir o .7z
    para cada post, melhorando drasticamente a performance.
    """
    commented_post_ids = set()
    answered_post_ids = set()
    temp_dir = tempfile.mkdtemp()
    try:
        with py7zr.SevenZipFile(site_archive_path, mode='r') as archive:
            targets = [f for f in archive.getnames() if f in [
                "Comments.xml", "Posts.xml"]]
            if not targets:
                return commented_post_ids, answered_post_ids

            archive.extract(path=temp_dir, targets=targets)

            # Processa Comments.xml
            comments_xml_path = os.path.join(temp_dir, "Comments.xml")
            if os.path.exists(comments_xml_path):
                context = ET.iterparse(comments_xml_path, events=("start",))
                for _, elem in context:
                    if elem.tag == "row":
                        post_id = elem.attrib.get("PostId")
                        if post_id:
                            commented_post_ids.add(post_id)
                    elem.clear()

            # Processa Posts.xml para encontrar respostas (ParentId)
            posts_xml_path = os.path.join(temp_dir, "Posts.xml")
            if os.path.exists(posts_xml_path):
                context = ET.iterparse(posts_xml_path, events=("start",))
                for _, elem in context:
                    if elem.tag == "row" and elem.attrib.get("PostTypeId") == "2":
                        parent_id = elem.attrib.get("ParentId")
                        if parent_id:
                            answered_post_ids.add(parent_id)
                    elem.clear()
    except Exception as e:
        print(f"  AVISO: Erro ao pré-carregar comentários/respostas: {e}")
    finally:
        shutil.rmtree(temp_dir)
    return commented_post_ids, answered_post_ids


def find_and_save_related_posts(related_tags):
    """Procura e salva posts que tenham as tags relacionadas e pelo menos uma resposta/comentário."""
    if not related_tags:
        print("Nenhuma tag relacionada para processar.")
=======
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
>>>>>>> ac736632fc5c62e2503c0771d5f26234978aaa44
        return

    initialize_csv(POSTS_OUTPUT)

    site_post_counts = {}

    for site_alias, site_name in SITES.items():
<<<<<<< HEAD
        site_archive = os.path.join(BASE_DIR, f"{site_name}")
        site_count = 0

        if not os.path.exists(site_archive):
            print(
                f"AVISO: Arquivo compactado não encontrado para '{site_alias}' em: {site_archive}")
=======
        if site_alias not in site_post_ids:
>>>>>>> ac736632fc5c62e2503c0771d5f26234978aaa44
            continue

        ids_to_find = site_post_ids[site_alias]
        archive_path = os.path.join(BASE_DIR, site_name)

<<<<<<< HEAD
        # Pré-carrega os IDs de posts com atividade para otimização
        print("  Pré-carregando IDs de posts com comentários e respostas...")
        commented_ids, answered_ids = preload_commented_and_answered_posts(
            site_archive)
        active_post_ids = commented_ids.union(answered_ids)

        with py7zr.SevenZipFile(site_archive, mode='r') as archive:
            # Assumimos que há apenas um Posts.xml por site
            posts_xml_path = "Posts.xml"
            if posts_xml_path not in archive.getnames():
                print(f"  AVISO: Posts.xml não encontrado em {site_archive}")
                continue

            file_count = 0
            # Extrai para um diretório temporário para manter a compatibilidade
            temp_dir = tempfile.mkdtemp()
            try:
                archive.extract(path=temp_dir, targets=[posts_xml_path])
                xml_path = os.path.join(temp_dir, posts_xml_path)

                context = ET.iterparse(xml_path, events=("start",))
                for _, elem in context:
                    if elem.tag != "row":
                        continue

                    post_id = elem.attrib.get("Id")
                    if post_id in processed_posts:
                        elem.clear()
                        continue

                    tags_field = elem.attrib.get("Tags", "")
                    if tags_field:
                        # Correção: Extrai tags do formato <tag1><tag2>
                        post_tags = set(re.findall(r'<(.+?)>', tags_field))
                        if not related_tags.isdisjoint(post_tags):
                            # Verificação otimizada: checa se o post_id está no conjunto pré-carregado
                            if post_id not in active_post_ids:
                                elem.clear()
                                continue

                            row = [
                                site_alias,
                                ";".join(post_tags),
                                post_id,
                                elem.attrib.get(
                                    "AcceptedAnswerId", ""),
                                elem.attrib.get("AnswerCount", "0"),
                                safe_date(elem.attrib.get(
                                    "CreationDate", "")),
                                safe_date(elem.attrib.get(
                                    "LastActivityDate", "")),
                                safe_date(elem.attrib.get(
                                    "LastEditDate", "")),
                                elem.attrib.get("OwnerUserId", ""),
                                elem.attrib.get("Score", "0"),
                                elem.attrib.get("ViewCount", "0"),
                                elem.attrib.get("Title", ""),
                                elem.attrib.get("Body", ""),
                                post_id,
                                site_name
                            ]

                            with open(RELEATED_POSTS, "a", encoding="utf-8", newline="") as f_csv:
                                csv.writer(f_csv).writerow(row)

                            processed_posts.add(post_id)
                            site_count += 1
                            file_count += 1

                    elem.clear()
            finally:
                shutil.rmtree(temp_dir)

            # registra quantos posts foram extraídos deste arquivo
            file_post_counts.append(
                (f"{site_alias}/{posts_xml_path}", file_count))
            print(f"  → Arquivo: {posts_xml_path} -> {file_count} posts")

        site_post_counts[site_alias] = site_count
        print(f"→ {site_alias}: {site_count} posts encontrados ")
=======
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
>>>>>>> ac736632fc5c62e2503c0771d5f26234978aaa44

    # --- resumo final ---
    print("\nResumo final:")
    total = 0
    for site, count in site_post_counts.items():
        print(f"  - {site}: {count} posts válidos")
        total += count
    print(f"\n Total geral: {total} posts extraídos")
    print(f"Arquivo consolidado salvo em: {POSTS_OUTPUT}")

<<<<<<< HEAD

=======
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
>>>>>>> ac736632fc5c62e2503c0771d5f26234978aaa44
if __name__ == "__main__":
    print("Iniciando 4get_posts.py ...")
    extract_posts_from_archives()
    print("Processamento concluído com sucesso!")
