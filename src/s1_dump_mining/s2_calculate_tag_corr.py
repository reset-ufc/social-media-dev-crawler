import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import xml.etree.ElementTree as ET
import py7zr
import tempfile
from collections import Counter
from utils_global import *
from paths import *


logger = get_logger(__name__)


def calculate_tag_counts_all_sites():
    """
    Calcula 'b' (ocorrência total de cada tag em perguntas) para TODOS os sites juntos.
    """
    logger.info("-> Calculando 'b' para TODOS os sites...")
    tag_occurrence_counter = Counter()  # Para a métrica 'b' agregada

    for site_alias, site_file in SITES.items():
        logger.info(f"  Processando site: {site_alias}...")
        archive_path = os.path.join(DUMP, site_file)
        
        if not os.path.exists(archive_path):
            logger.warning(f"    .7z não encontrado para {site_alias}: {archive_path}")
            continue
            
        try:
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                posts_files = [f for f in archive.getnames() if "Posts.xml" in f]
                if not posts_files:
                    logger.warning(f"    Nenhum Posts.xml dentro de {archive_path}")
                    continue

                with tempfile.TemporaryDirectory() as temp_dir:
                    archive.extract(path=temp_dir, targets=posts_files)
                    posts_path = os.path.join(temp_dir, posts_files[0])

                    context = ET.iterparse(posts_path, events=("end",))
                    for _, elem in context:
                        if elem.tag == "row" and elem.attrib.get("PostTypeId") == "1":
                            tags_field = elem.attrib.get("Tags", "")
                            if tags_field:
                                post_tags = extract_tag_list(tags_field)
                                tag_occurrence_counter.update(post_tags)
                        elem.clear()
                    del context
        except Exception as e:
            logger.error(f"    Erro ao processar {archive_path}: {e}", exc_info=True)

    # Cria o DataFrame com as contagens totais agregadas
    df_counts = pd.DataFrame(
        tag_occurrence_counter.items(), columns=['tag', 'b'])

    logger.info(f"  Contagem total agregada: {len(df_counts)} tags únicas de todos os sites.")
    return df_counts


def calculate_a_and_c_all_sites():
    """
    Calcula 'a' (coocorrência com a QUESTION_TAG) e 'c' (total de perguntas com a QUESTION_TAG)
    considerando TODOS os sites juntos.
    Retorna um DataFrame com a métrica 'a' e o valor de 'c' agregado.
    """
    logger.info("-> Calculando 'a' e 'c' para TODOS os sites...")
    
    if not os.path.exists(COARSE_QUESTIONS):
        logger.error(f"Arquivo {COARSE_QUESTIONS} não encontrado.")
        return pd.DataFrame(), 0

    df = pd.read_csv(COARSE_QUESTIONS, dtype=str)
    logger.info(f"  Total de posts em {os.path.basename(str(COARSE_QUESTIONS))}: {len(df)}")

    df['tags'] = df['tags'].fillna('')
    df['tag_list'] = df['tags'].apply(extract_tag_list)

    # Filtra posts que contêm a tag principal (de TODOS os sites)
    df_filtered = df[df['tag_list'].apply(lambda L: QUESTION_TAG in L)]
    c = len(df_filtered)
    logger.info(f"  Constante 'c' calculada (todos os sites): {c}")

    if c == 0:
        logger.warning("Nenhum post encontrado com a tag principal. Não é possível calcular 'a'.")
        return pd.DataFrame(), c

    # Conta a coocorrência de todas as tags nesses posts filtrados
    all_tags_in_filtered_posts = df_filtered['tag_list'].explode().dropna()
    tag_counts_a = all_tags_in_filtered_posts.value_counts()

    df_a = tag_counts_a.reset_index()
    df_a.columns = ['tag', 'a']

    logger.info(f"  Métrica 'a' calculada para {len(df_a)} tags únicas.")
    return df_a, c


def calculate_heuristics_and_filter(df_counts, df_a, c):
    """
    Junta as métricas, calcula as heurísticas H1 e H2, e filtra as tags.
    Gera um único arquivo de saída: related_tags.csv
    """
    logger.info("-> Unindo métricas, calculando heurísticas e filtrando...")

    # Junta as contagens totais (b) com as de coocorrência (a)
    df = pd.merge(df_counts, df_a, on='tag', how='left').fillna(0)
    df['a'] = df['a'].astype(int)

    # Remove a própria tag principal da lista de tags relacionadas
    df = df[df['tag'] != QUESTION_TAG].reset_index(drop=True)
    logger.info(f"  Total de tags candidatas antes da filtragem: {len(df)}")

    # --- Calcular H1 = a / b ---
    df['h1'] = df.apply(lambda row: row['a'] / row['b'] if row['b'] > 0 else 0, axis=1)

    # --- Calcular H2 = a / c ---
    if c > 0:
        df['h2'] = df['a'] / c
    else:
        logger.warning("Valor de c=0, definindo h2 como 0 para todas as tags.")
        df['h2'] = 0

    # --- Filtragem ---
    initial_count = len(df)

    # Filtro H1
    df_h1_filtered = df[df['h1'] >= THRE1]
    h1_removed_count = initial_count - len(df_h1_filtered)
    logger.info(f"  Filtro H1 (h1 >= {THRE1}): {h1_removed_count} tags removidas.")

    # Filtro H2
    df_h2_filtered = df_h1_filtered[df_h1_filtered['h2'] >= THRE2]
    h2_removed_count = len(df_h1_filtered) - len(df_h2_filtered)
    logger.info(f"  Filtro H2 (h2 >= {THRE2}): {h2_removed_count} tags removidas.")

    final_df = df_h2_filtered.sort_values(by=['h1', 'h2'], ascending=False)

    # Define o caminho de saída único
    ensure_parent_dir(R_TAGS)

    # Salva o resultado final
    final_df.to_csv(R_TAGS, index=False, encoding='utf-8')
    logger.info(f"  Filtragem concluída. {len(final_df)} tags salvas em: {R_TAGS}")
    
    return final_df


def main():
    ensure_parent_dir(COARSE_QUESTIONS)
    logger.info("Iniciando processo de cálculo de heurísticas agregadas (todos os sites)...")
    
    logger.info(f"\n{'='*20} PROCESSANDO TODOS OS SITES COMO UM CORPO ÚNICO {'='*20}\n")
    
    # 1. Calcula as contagens totais de todas as tags (b) para TODOS os sites
    df_counts = calculate_tag_counts_all_sites()
    
    # 2. Calcula a coocorrência (a) e o total de posts da tag principal (c) para TODOS os sites
    df_a, c = calculate_a_and_c_all_sites()
    
    # 3. Junta tudo, calcula as heurísticas e filtra
    if not df_a.empty and c > 0 and not df_counts.empty:
        final_df = calculate_heuristics_and_filter(df_counts, df_a, c)
        
        logger.info("\n##### RESUMO FINAL #####")
        logger.info(f"  - Total de tags únicas analisadas: {len(df_counts)}")
        logger.info(f"  - Total de perguntas com '{QUESTION_TAG}': {c}")
        logger.info(f"  - Tags relacionadas após filtragem: {len(final_df)}")
        logger.info("##### FIM DO RESUMO #####\n")
    else:
        logger.warning("Não foi possível prosseguir com o cálculo das heurísticas devido a dados ausentes (a, b ou c).")

    logger.info("Processo de cálculo de heurísticas de tags finalizado.")


if __name__ == "__main__":
    main() 