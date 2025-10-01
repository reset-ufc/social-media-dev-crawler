import pandas as pd
import xml.etree.ElementTree as ET
import os
from collections import Counter
from config import *


def make_releated_tags():
    """
    Lê o arquivo CSV de perguntas, extrai todas as tags, conta a ocorrência de cada uma
    e salva o resultado em um novo arquivo CSV com a coluna 'a'.
    """
    try:
        df_coarse = pd.read_csv(COARSE_QUESTIONS)
    except FileNotFoundError:
        print(f"ERRO: Arquivo de perguntas não encontrado: {COARSE_QUESTIONS}.")
        return

    if 'tags' not in df_coarse.columns:
        print(f"ERRO: Coluna 'tags' não encontrada em {COARSE_QUESTIONS}.")
        return

    df_coarse.dropna(subset=['tags'], inplace=True)
    explode_tags = df_coarse['tags'].str.split(';').explode()
    tag_counts_series = explode_tags.value_counts()

    releated_tags_df = tag_counts_series.reset_index()
    releated_tags_df.columns = ['tag', 'a']

    if QUESTION_TAG in releated_tags_df['tag'].values:
        releated_tags_df = releated_tags_df[releated_tags_df['tag']
                                            != QUESTION_TAG]

    releated_tags_df.to_csv(RELEATED_TAGS, index=False)
    print(
        f"Arquivo de tags relacionadas (coluna 'a') salvo em: {RELEATED_TAGS}")


def calculate_b():
    """
    Calcula a coluna 'b': a contagem de cada tag diretamente dos arquivos Posts.xml originais.
    """
    print("Calculando a coluna 'b' a partir dos arquivos de dump originais...")
    tag_counter = Counter()

    for site_alias, site_name in SITES.items():
        posts_path = os.path.join(BASE_DIR, site_name, "Posts.xml")
        if not os.path.exists(posts_path):
            print(
                f"AVISO: Arquivo Posts.xml não encontrado para o site '{site_alias}' em: {posts_path}")
            continue

        print(f"Processando: {posts_path}")
        context = ET.iterparse(posts_path, events=("start",))
        for _, elem in context:
            if elem.tag == "row":
                tags_field = elem.attrib.get("Tags", "")
                if tags_field:
                    tags = tags_field.strip('|').split('|')
                    tag_counter.update(tags)
            elem.clear()

    if not tag_counter:
        print("Nenhuma tag encontrada nos arquivos de dump.")
        return

    b_df = pd.DataFrame(tag_counter.items(), columns=['tag', 'b'])

    try:
        a_df = pd.read_csv(RELEATED_TAGS)
    except FileNotFoundError:
        print(
            f"ERRO: Arquivo {RELEATED_TAGS} não encontrado. Execute make_releated_tags() primeiro.")
        return

    merged_df = pd.merge(a_df, b_df, on='tag', how='left')

    merged_df.to_csv(RELEATED_TAGS, index=False)
    print(f"Coluna 'b' adicionada e arquivo salvo em: {RELEATED_TAGS}")


def calculate_h1():
    """
    Calcula a coluna h1 como a/b.
    """
    print("Calculando a coluna 'h1'...")
    try:
        df = pd.read_csv(RELEATED_TAGS)
    except FileNotFoundError:
        print(
            f"ERRO: Arquivo {RELEATED_TAGS} não encontrado. Execute as funções anteriores primeiro.")
        return

    if 'a' not in df.columns or 'b' not in df.columns:
        print("ERRO: Colunas 'a' ou 'b' não encontradas. Execute as funções anteriores primeiro.")
        return

    # Calcula h1 = a / b. Onde b for 0 ou nulo, o resultado será 0 para evitar erros.
    df['h1'] = (df['a'] / df['b']).fillna(0)

    df.to_csv(RELEATED_TAGS, index=False)
    print(f"Coluna 'h1' adicionada e arquivo salvo em: {RELEATED_TAGS}")


def filter_by_h1_threshold():                                                                                                
    """                                                                                                                      
    Filtra o arquivo de tags relacionadas, removendo linhas onde 'h1' é menor que thre1.                                     
    """                                                                                                                      
    print(f"Filtrando tags com h1 < {THRE1}...")                                                                             
    try:                                                                                                                     
        df = pd.read_csv(RELEATED_TAGS)                                                                                      
    except FileNotFoundError:                                                                                                
        print(                                                                                                               
            f"ERRO: Arquivo {RELEATED_TAGS} não encontrado. Execute as funções anteriores primeiro.")  
        return                                                                                                               
            
    if 'h1' not in df.columns:                                                                                               
        print("ERRO: Coluna 'h1' não encontrada. Execute calculate_h1() primeiro.")              
        return                                                                                                               

    original_rows = len(df)                                                                                               
    df = df[df['h1'] >= THRE1]                                                                                            
    new_rows = len(df)                                                                                                    

    df.to_csv(RELEATED_TAGS, index=False)                                                                                 
    print(f"Filtro aplicado. {original_rows - new_rows} linhas removidas.")                                               
    print(f"Arquivo de tags relacionadas atualizado salvo em: {RELEATED_TAGS}")   


if __name__ == "__main__":
    make_releated_tags()
    calculate_b()
    calculate_h1()
    filter_by_h1_threshold()
