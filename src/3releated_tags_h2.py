import pandas as pd
import os
import xml.etree.ElementTree as ET
from config import *
import re

# --- mesma função de H1, para consistência ---
def extract_tag_list(tags_field):
    if not isinstance(tags_field, str) or tags_field.strip() == "":
        return []
    if '<' in tags_field and '>' in tags_field:
        return re.findall(r'<(.+?)>', tags_field)
    if ';' in tags_field:
        return [t.strip() for t in tags_field.split(';') if t.strip()]
    if '|' in tags_field:
        return [t.strip() for t in tags_field.split('|') if t.strip()]
    return [t.strip() for t in re.split(r'[\s,;|]+', tags_field) if t.strip()]


def calculate_c():
    """
    Calcula c = número total de perguntas nos arquivos Posts.xml que contêm QUESTION_TAG.
    """
    print("Calculando a constante 'c' ...")
    c = 0

    for site_alias, site_name in SITES.items():
        posts_path = os.path.join(BASE_DIR, site_name, "Posts.xml")
        if not os.path.exists(posts_path):
            print(f"AVISO: Posts.xml não encontrado em: {posts_path}")
            continue

        print(f"Processando: {posts_path}")
        context = ET.iterparse(posts_path, events=("start",))
        for _, elem in context:
            if elem.tag == "row" and elem.attrib.get("PostTypeId") == "1":
                tags_field = elem.attrib.get("Tags", "")
                tags = extract_tag_list(tags_field)
                if QUESTION_TAG in tags:
                    c += 1
            elem.clear()

    print(f"Constante c = {c}")
    return c


def calculate_h2():
    """
    Calcula h2 = a / c e grava no arquivo de tags relacionadas.
    """
    print("Calculando h2 ...")

    if not os.path.exists(RELEATED_TAGS):
        print(f"ERRO: {RELEATED_TAGS} não encontrado. Rode H1 primeiro.")
        return

    df = pd.read_csv(RELEATED_TAGS)

    if 'a' not in df.columns:
        print("ERRO: coluna 'a' não encontrada. Rode make_releated_tags() primeiro.")
        return

    df['a'] = pd.to_numeric(df['a'], errors='coerce').fillna(0).astype(int)

    c = calculate_c()
    if c <= 0:
        print("ERRO: valor de c = 0. Não é possível calcular h2.")
        return

    df['h2'] = (df['a'] / c).fillna(0)

    df.to_csv(RELEATED_TAGS, index=False)
    print(f"Coluna 'h2' adicionada. Arquivo atualizado: {RELEATED_TAGS}")


def filter_by_h2_threshold():
    """
    Remove linhas com h2 < THRE2.
    """
    print(f"Filtrando tags com h2 < {THRE2} ...")

    if not os.path.exists(RELEATED_TAGS):
        print(f"ERRO: {RELEATED_TAGS} não encontrado.")
        return

    df = pd.read_csv(RELEATED_TAGS)

    if 'h2' not in df.columns:
        print("ERRO: coluna 'h2' não encontrada. Rode calculate_h2() primeiro.")
        return

    original = len(df)
    df = df[df['h2'] >= THRE2].reset_index(drop=True)
    removed = original - len(df)

    df.to_csv(RELEATED_TAGS, index=False)
    print(f"Filtro aplicado. {removed} tags removidas. Arquivo salvo: {RELEATED_TAGS}")


if __name__ == "__main__":
    calculate_h2()
    filter_by_h2_threshold()
