import os
import csv
import xml.etree.ElementTree as ET
import datetime

from config import *


question_features = [
    'site', 'tags', 'question_id', 'accepted_answer_id', 'answer_count',
    'creation_date', 'last_activity_date', 'last_edit_date',
    'owner_id', 'score', 'view_count', 'title', 'body'
]


def initiateCSVs():
    # criação do csv de questões
    with open(COARSE_QUESTIONS, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(question_features)


def safe_date(ts):

    try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
        return dt.strftime('%Y/%m/%d, %H:%M:%S')
    except Exception:

        return ts


def parse_posts(site_alias):

    site_name = SITES[site_alias]
    folder = os.path.join(BASE_DIR, site_name)
    posts_path = os.path.join(folder, "Posts.xml") #qual arquivo vai procurar nos sites
    if not os.path.exists(posts_path):
        print(f"[{site_alias}] Posts.xml não encontrado em: {posts_path}")
        return

    print(f"[{site_alias}] Processando Posts: {posts_path}")

    context = ET.iterparse(posts_path, events=("start",))
    for _, elem in context:
        if elem.tag == "row":
            post_type = elem.attrib.get("PostTypeId")

            if post_type == "1":
                tags_field = elem.attrib.get("Tags", "")
                # Apenas processa se o campo de tags não estiver vazio
                if tags_field:
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


if __name__ == "__main__":
    print("Inicializando CSVs …")
    initiateCSVs()

    for site_alias in SITES.keys():
        parse_posts(site_alias)

    print("Processamento concluído!")
