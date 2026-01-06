import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess
import pandas as pd
import xml.etree.ElementTree as ET
from collections import Counter
from utils_global import *
from paths import *


logger = get_logger(__name__)


def calculate_tag_counts_all_sites():
    """
    Calcula 'b' (ocorrência total de cada tag em perguntas) para TODOS os sites juntos.
    """
    logger.info("-> Calculando 'b' para TODOS os sites (Streaming Otimizado)...")
    tag_occurrence_counter = Counter()

    for site_alias, site_file in SITES.items():
        logger.info(f"  Processando site: {site_alias}...")
        archive_path = os.path.join(DUMP, site_file)
        
        if not os.path.exists(archive_path):
            logger.warning(f"    .7z não encontrado para {site_alias}: {archive_path}")
            continue

        with stream_posts_from_7z(archive_path) as context:
            for _, elem in context:
                if elem.tag == "row" and elem.attrib.get("PostTypeId") == "1":
                    tags_field = elem.attrib.get("Tags", "")
                    if tags_field:
                        post_tags = extract_tag_list(tags_field)
                        tag_occurrence_counter.update(post_tags)
                elem.clear()

    df_counts = pd.DataFrame(
        tag_occurrence_counter.items(), columns=['tag', 'b']
    )

    logger.info(f"  Contagem total agregada: {len(df_counts)} tags únicas de todos os sites.")
    return df_counts



def calculate_a_and_c_all_sites():
    logger.info("-> Calculando 'a' e 'c' para TODOS os sites...")
    
    if not os.path.exists(COARSE_QUESTIONS):
        logger.error(f"Arquivo {COARSE_QUESTIONS} não encontrado.")
        return pd.DataFrame(), 0

    df = pd.read_csv(COARSE_QUESTIONS, dtype=str)
    logger.info(f"  Total de posts em {os.path.basename(str(COARSE_QUESTIONS))}: {len(df)}")

    df['tags'] = df['tags'].fillna('')
    df['tag_list'] = df['tags'].apply(extract_tag_list)

    df_filtered = df[df['tag_list'].apply(lambda L: QUESTION_TAG in L)]
    c = len(df_filtered)
    logger.info(f"  Constante 'c' calculada (todos os sites): {c}")

    if c == 0:
        logger.warning("Nenhum post encontrado com a tag principal. Não é possível calcular 'a'.")
        return pd.DataFrame(), c

    all_tags_in_filtered_posts = df_filtered['tag_list'].explode().dropna()
    tag_counts_a = all_tags_in_filtered_posts.value_counts()

    df_a = tag_counts_a.reset_index()
    df_a.columns = ['tag', 'a']

    logger.info(f"  Métrica 'a' calculada para {len(df_a)} tags únicas.")
    return df_a, c


def calculate_heuristics_and_filter(df_counts, df_a, c):
    logger.info("-> Unindo métricas, calculando heurísticas e filtrando...")

    df = pd.merge(df_counts, df_a, on='tag', how='left').fillna(0)
    df['a'] = df['a'].astype(int)
    df = df[df['tag'] != QUESTION_TAG].reset_index(drop=True)

    df['h1'] = df.apply(lambda row: row['a'] / row['b'] if row['b'] > 0 else 0, axis=1)

    if c > 0:
        df['h2'] = df['a'] / c
    else:
        df['h2'] = 0

    df_h1_filtered = df[df['h1'] >= THRE1]
    df_h2_filtered = df_h1_filtered[df_h1_filtered['h2'] >= THRE2]

    final_df = df_h2_filtered.sort_values(by=['h1', 'h2'], ascending=False)
    ensure_parent_dir(R_TAGS)
    final_df.to_csv(R_TAGS, index=False, encoding='utf-8')
    
    return final_df


def main():
    ensure_parent_dir(COARSE_QUESTIONS)
    logger.info("Iniciando processo de cálculo de heurísticas agregadas (Zero-Disk)...")
    
    df_counts = calculate_tag_counts_all_sites()
    df_a, c = calculate_a_and_c_all_sites()
    
    if not df_a.empty and c > 0 and not df_counts.empty:
        final_df = calculate_heuristics_and_filter(df_counts, df_a, c)
        logger.info(f"Sucesso. Tags salvas: {len(final_df)}")
    else:
        logger.warning("Dados insuficientes para calcular heurísticas.")

if __name__ == "__main__":
    main()