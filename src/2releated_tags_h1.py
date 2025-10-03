import pandas as pd
import xml.etree.ElementTree as ET
import os
import re
from collections import Counter
from config import *

# --- Utils ---------------------------------------------------------
def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

def extract_tag_list(tags_field):
    """
    Recebe o valor bruto da coluna tags e retorna lista de tags.
    Suporta formatos comuns:
      - "<python><cryptography>"
      - "python;cryptography"
      - "python|cryptography"
      - "python cryptography" (ou separados por vírgula/semicolons/pipe/spaces)
    """
    if pd.isna(tags_field) or tags_field == "":
        return []
    # se formato com <tag>
    if '<' in tags_field and '>' in tags_field:
        return re.findall(r'<(.+?)>', tags_field)
    # se for separador ponto-e-vírgula
    if ';' in tags_field:
        return [t.strip() for t in tags_field.split(';') if t.strip()]
    # se for pipe
    if '|' in tags_field:
        return [t.strip() for t in tags_field.split('|') if t.strip()]
    # fallback: split por espaço, vírgula, ; ou |
    return [t.strip() for t in re.split(r'[\s,;|]+', tags_field) if t.strip()]


# --- Funções principais -------------------------------------------
def make_releated_tags():
    """
    Lê COARSE_QUESTIONS, normaliza tags, filtra posts que contém QUESTION_TAG
    e conta ocorrência de cada tag (coluna 'a'). Salva em RELEATED_TAGS.
    """
    print("-> make_releated_tags: começando...")
    if not os.path.exists(COARSE_QUESTIONS):
        print(f"ERRO: arquivo {COARSE_QUESTIONS} não encontrado. Verifique config.py e paths.")
        return

    df = pd.read_csv(COARSE_QUESTIONS, dtype=str)
    print(f"  Linhas totais lidas em {COARSE_QUESTIONS}: {len(df)}")

    if 'tags' not in df.columns:
        print("ERRO: coluna 'tags' não encontrada no CSV de perguntas.")
        return

    df['tags'] = df['tags'].fillna('')

    # normaliza em lista
    df['tag_list'] = df['tags'].apply(extract_tag_list)

    # quantas têm QUESTION_TAG?
    num_with_question_tag = df['tag_list'].apply(lambda L: QUESTION_TAG in L).sum()
    print(f"  Posts que contém a tag principal '{QUESTION_TAG}': {num_with_question_tag}")

    # filtra apenas os posts que contém QUESTION_TAG
    df_filtered = df[df['tag_list'].apply(lambda L: QUESTION_TAG in L)]

    # explode e conta
    all_tags = df_filtered['tag_list'].explode().dropna()
    if all_tags.empty:
        print("  ATENÇÃO: nenhum tag extraída (lista vazia). O CSV resultante conterá apenas cabeçalho.")
    tag_counts = all_tags.value_counts()

    # monta DataFrame
    releated_tags_df = tag_counts.reset_index()
    releated_tags_df.columns = ['tag', 'a']

    # remove a própria QUESTION_TAG (se presente)
    if QUESTION_TAG in releated_tags_df['tag'].values:
        releated_tags_df = releated_tags_df[releated_tags_df['tag'] != QUESTION_TAG]

    # garante diretório e salva
    ensure_parent_dir(RELEATED_TAGS)
    releated_tags_df.to_csv(RELEATED_TAGS, index=False, encoding='utf-8')
    print(f"  Arquivo salvo em: {RELEATED_TAGS} (linhas: {len(releated_tags_df)})")
    if len(releated_tags_df) > 0:
        print("  Top 10 tags (a):")
        print(releated_tags_df.head(10).to_string(index=False))


def calculate_b():
    """
    Conta b: número de posts no dump original que possuem cada tag.
    Usa RELEATED_TAGS como lista de tags a considerar (para não contar tudo).
    """
    print("-> calculate_b: começando...")
    if not os.path.exists(RELEATED_TAGS):
        print(f"ERRO: arquivo {RELEATED_TAGS} não encontrado. Execute make_releated_tags() primeiro.")
        return

    releated_tags_df = pd.read_csv(RELEATED_TAGS, dtype={'tag': str})
    tags_to_count = set(releated_tags_df['tag'].dropna().astype(str))
    tag_counter = Counter()

    for site_alias, site_name in SITES.items():
        posts_path = os.path.join(BASE_DIR, site_name, "Posts.xml")
        if not os.path.exists(posts_path):
            print(f"  AVISO: Posts.xml não encontrado para {site_alias} em {posts_path}")
            continue
        print(f"  Processando dump: {posts_path} ...")
        context = ET.iterparse(posts_path, events=("start",))
        for _, elem in context:
            if elem.tag == "row":
                tags_field = elem.attrib.get("Tags", "")
                if tags_field:
                    # extrai tags no formato <tag> 
                    tags_in_post = extract_tag_list(tags_field)
                    for t in tags_in_post:
                        if t in tags_to_count:
                            tag_counter.update([t])
            elem.clear()

    # mapeia contagens para dataframe
    releated_tags_df['b'] = releated_tags_df['tag'].map(tag_counter).fillna(0).astype(int)
    releated_tags_df.to_csv(RELEATED_TAGS, index=False, encoding='utf-8')
    print(f"  Coluna 'b' adicionada e arquivo salvo em: {RELEATED_TAGS}")


def calculate_h1():
    print("-> calculate_h1: começando...")
    if not os.path.exists(RELEATED_TAGS):
        print(f"ERRO: arquivo {RELEATED_TAGS} não encontrado.")
        return
    df = pd.read_csv(RELEATED_TAGS, dtype={'a': float, 'b': float})
    if 'a' not in df.columns or 'b' not in df.columns:
        print("ERRO: colunas 'a' e 'b' necessárias não existem.")
        return
    # divisão segura
    df['h1'] = (df['a'] / df['b']).replace([float('inf'), -float('inf')], 0).fillna(0)
    df.to_csv(RELEATED_TAGS, index=False, encoding='utf-8')
    print(f"  Coluna 'h1' calculada e salva em {RELEATED_TAGS}.")


def filter_by_h1_threshold():
    print("-> filter_by_h1_threshold: começando...")
    if not os.path.exists(RELEATED_TAGS):
        print(f"ERRO: arquivo {RELEATED_TAGS} não encontrado.")
        return
    df = pd.read_csv(RELEATED_TAGS)
    if 'h1' not in df.columns:
        print("ERRO: coluna 'h1' não encontrada. Execute calculate_h1() primeiro.")
        return
    original = len(df)
    df = df[df['h1'] >= THRE1]
    df.to_csv(RELEATED_TAGS, index=False, encoding='utf-8')
    print(f"  Filtragem por THRE1={THRE1} aplicada. Removidas {original - len(df)} linhas. Salvo em {RELEATED_TAGS}")


#função main
if __name__ == "__main__":
    ensure_parent_dir(COARSE_QUESTIONS)  # só garante pastas se desejar
    make_releated_tags()
    calculate_b()
    calculate_h1()
    filter_by_h1_threshold()
    print("Processo finalizado.")
