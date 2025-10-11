import os
import csv
import xml.etree.ElementTree as ET
import py7zr
import tempfile
import shutil

from paths import *
from utils import *


question_features = [
    'site', 'tags', 'question_id', 'accepted_answer_id', 'answer_count',
    'creation_date', 'last_activity_date', 'last_edit_date',
    'owner_id', 'score', 'view_count', 'title', 'body'
]

def initiateCSVs():
    """Cria o CSV principal com cabeçalhos, se não existir."""
    ensure_parent_dir(COARSE_QUESTIONS)
    if not os.path.exists(COARSE_QUESTIONS):
        with open(COARSE_QUESTIONS, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(question_features)


def parse_posts_from_7z(site_alias):
    """Extrai e processa apenas o arquivo Posts.xml de dentro do .7z."""
    site_file = SITES[site_alias]
    archive_path = os.path.join(BASE_DIR, site_file)

    if not os.path.exists(archive_path):
        print(f"[{site_alias}] Arquivo não encontrado: {archive_path}")
        return

    print(f"[{site_alias}] Lendo arquivo compactado: {archive_path}")

    try:
        with py7zr.SevenZipFile(archive_path, mode='r') as archive:
            file_list = archive.getnames()
            posts_files = [f for f in file_list if "Posts.xml" in f]
            if not posts_files:
                print(f"[{site_alias}] Nenhum Posts.xml encontrado dentro do .7z.")
                return

            # Criar pasta temporária
            temp_dir = tempfile.mkdtemp()
            archive.extract(path=temp_dir, targets=posts_files)
            posts_path = os.path.join(temp_dir, posts_files[0])

            print(f"[{site_alias}] Processando {posts_path} ...")

            context = ET.iterparse(posts_path, events=("start",))
            for _, elem in context:
                if elem.tag == "row" and elem.attrib.get("PostTypeId") == "1":
                    tags_field = elem.attrib.get("Tags", "")
                    if not tags_field:
                        continue

                    all_tags = tags_field.strip('|').split('|')
                    tags_str = ";".join(all_tags)

                    row = [
                        site_alias,
                        tags_str,
                        elem.attrib.get("Id"),
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

                    with open(COARSE_QUESTIONS, "a", encoding="utf-8", newline="") as f:
                        csv.writer(f).writerow(row)
                elem.clear()
            del context  # Garante que o arquivo XML seja liberado

            # Limpa o arquivo temporário
            shutil.rmtree(temp_dir)

    except Exception as e:
        print(f"[{site_alias}] Erro ao processar {archive_path}: {e}")

def main():
    print("Inicializando CSVs …")
    initiateCSVs()

    for site_alias in SITES.keys():
        parse_posts_from_7z(site_alias)

    print("Processamento concluído!")

if __name__ == "__main__":
    main()
