import os
import csv
import pandas as pd
import xml.etree.ElementTree as ET
import datetime
from config import *

# Re-using the features from 1get_main_tag.py
POST_FEATURES = [
    'site', 'tags', 'question_id', 'accepted_answer_id', 'answer_count',
    'creation_date', 'last_activity_date', 'last_edit_date',
    'owner_id', 'score', 'view_count', 'title', 'body'
]

def safe_date(ts):
    """Converts a date string to a standard format, handling potential errors."""
    try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
        return dt.strftime('%Y/%m/%d, %H:%M:%S')
    except (ValueError, TypeError):
        return ts

def get_related_tags():
    """Reads releated_tags.csv and returns a set of tags for quick lookup."""
    try:
        df = pd.read_csv(RELEATED_TAGS)
        return set(df['tag'])
    except FileNotFoundError:
        print(f"ERRO: Arquivo de tags relacionadas não encontrado: {RELEATED_TAGS}")
        return set()

def initialize_csv():
    """Creates the CSV file for related posts with a header if it doesn't exist."""
    if not os.path.exists(RELEATED_POSTS):
        with open(RELEATED_POSTS, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(POST_FEATURES)

def find_and_save_related_posts(related_tags):
    """
    Finds posts in the original dumps that contain at least one of the related tags
    and saves them to the releated_posts.csv file.
    """
    if not related_tags:
        print("Nenhuma tag relacionada para processar.")
        return

    processed_posts = set()

    for site_alias, site_name in SITES.items():
        posts_path = os.path.join(BASE_DIR, site_name, "Posts.xml")
        if not os.path.exists(posts_path):
            print(f"AVISO: Arquivo Posts.xml não encontrado para o site '{site_alias}' em: {posts_path}")
            continue

        print(f"Processando: {posts_path}")
        context = ET.iterparse(posts_path, events=("start",))
        for _, elem in context:
            if elem.tag == "row":
                post_id = elem.attrib.get("Id")
                # Evita processar o mesmo post múltiplas vezes
                if post_id in processed_posts:
                    elem.clear()
                    continue

                tags_field = elem.attrib.get("Tags", "")
                if tags_field:
                    post_tags = set(tags_field.strip('|').split('|'))
                    # Verifica se há interseção entre as tags do post e as tags relacionadas
                    if not related_tags.isdisjoint(post_tags):
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
                        with open(RELEATED_POSTS, "a", encoding="utf-8", newline="") as f:
                            csv.writer(f).writerow(row)
                        
                        processed_posts.add(post_id)

            elem.clear()

if __name__ == "__main__":
    print("Inicializando...")
    initialize_csv()
    
    print("Carregando tags relacionadas...")
    tags_to_find = get_related_tags()
    
    print("Buscando e salvando posts relacionados...")
    find_and_save_related_posts(tags_to_find)
    
    print("Processamento concluído!")
