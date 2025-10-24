import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import xml.etree.ElementTree as ET
import py7zr
import tempfile
from collections import Counter
from utils import *
from paths import *


logger = get_logger(__name__)


def calculate_tag_counts(site_alias, site_file):
    """
    Calcula 'b' (ocorrência total de cada tag em perguntas) lendo o dump de um site.
    """
    logger.info(f"-> Calculando 'b' para o site: {site_alias}...")
    tag_occurrence_counter = Counter()  # Para a métrica 'b'

    archive_path = os.path.join(DUMP, site_file)
    if not os.path.exists(archive_path):
        logger.warning(
            f"  .7z não encontrado para {site_alias}: {archive_path}")
        return pd.DataFrame()
    try:
        with py7zr.SevenZipFile(archive_path, mode='r') as archive:
            posts_files = [f for f in archive.getnames() if "Posts.xml" in f]
            if not posts_files:
                logger.warning(f"  Nenhum Posts.xml dentro de {archive_path}")
                return pd.DataFrame()

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
        logger.error(f"Erro ao processar {archive_path}: {e}", exc_info=True)

    # Cria o DataFrame com as contagens totais
    df_counts = pd.DataFrame(
        tag_occurrence_counter.items(), columns=['tag', 'b'])

    logger.info(f"  Contagem total de {len(df_counts)} tags únicas concluída.")
    return df_counts


def calculate_a_and_c(site_alias):
    """
    Calcula 'a' (coocorrência com a QUESTION_TAG) e 'c' (total de perguntas com a QUESTION_TAG).
    Retorna um DataFrame com a métrica 'a' e o valor de 'c' para um site específico.
    """
    logger.info(f"-> Calculando 'a' e 'c' para o site: {site_alias}...")
    if not os.path.exists(COARSE_QUESTIONS):
        logger.error(f"Arquivo {COARSE_QUESTIONS} não encontrado.")
        return pd.DataFrame(), 0

    df = pd.read_csv(COARSE_QUESTIONS, dtype=str)

    # Filtra o dataframe de perguntas para o site atual
    df_site = df[df['site'] == site_alias].copy()
    logger.info(
        f"  Posts do site '{site_alias}' em {os.path.basename(str(COARSE_QUESTIONS))}: {len(df_site)}")

    df_site['tags'] = df_site['tags'].fillna('')
    df_site['tag_list'] = df_site['tags'].apply(extract_tag_list)

    # Filtra posts que contêm a tag principal
    df_filtered = df_site[df_site['tag_list'].apply(
        lambda L: QUESTION_TAG in L)]
    c = len(df_filtered)
    logger.info(f"  Constante 'c' calculada: {c}")

    if c == 0:
        logger.warning(
            "Nenhum post encontrado com a tag principal. Não é possível calcular 'a'.")
        return pd.DataFrame(), c

    # Conta a coocorrência de todas as tags nesses posts filtrados
    all_tags_in_filtered_posts = df_filtered['tag_list'].explode().dropna()
    tag_counts_a = all_tags_in_filtered_posts.value_counts()

    df_a = tag_counts_a.reset_index()
    df_a.columns = ['tag', 'a']

    return df_a, c


def calculate_heuristics_and_filter(df_counts, df_a, c, site_alias):
    """
    Junta as métricas, calcula as heurísticas H1 e H2, e filtra as tags.
    """
    logger.info(
        f"-> Unindo métricas, calculando heurísticas e filtrando para {site_alias}...")

    # Junta as contagens totais (b, d) com as de coocorrência (a)
    df = pd.merge(df_counts, df_a, on='tag', how='left').fillna(0)
    df['a'] = df['a'].astype(int)

    # Remove a própria tag principal da lista de tags relacionadas
    df = df[df['tag'] != QUESTION_TAG].reset_index(drop=True)
    logger.info(f"  Total de tags candidatas antes da filtragem: {len(df)}")

    # --- Calcular H1 = a / b ---
    # Evita divisão por zero
    df['h1'] = df.apply(lambda row: row['a'] / row['b']
                        if row['b'] > 0 else 0, axis=1)

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
    logger.info(
        f"  Filtro H1 (h1 >= {THRE1}): {h1_removed_count} tags removidas.")

    # Filtro H2
    df_h2_filtered = df_h1_filtered[df_h1_filtered['h2'] >= THRE2]
    h2_removed_count = len(df_h1_filtered) - len(df_h2_filtered)
    logger.info(
        f"  Filtro H2 (h2 >= {THRE2}): {h2_removed_count} tags removidas.")

    final_df = df_h2_filtered.sort_values(by=['h1', 'h2'], ascending=False)

    # Gera o caminho de saída dinamicamente para o site
    output_path = get_releated_tags_path(site_alias)
    ensure_parent_dir(output_path)

    # Salva o resultado final
    final_df.to_csv(output_path, index=False, encoding='utf-8')
    logger.info(
        f"  Filtragem concluída. {len(final_df)} tags salvas em: {output_path}")


def main():
    ensure_parent_dir(COARSE_QUESTIONS)
    logger.info("Iniciando processo de cálculo de heurísticas por site...")

    for site_alias, site_file in SITES.items():
        logger.info(
            f"\n{'='*20} PROCESSANDO SITE: {site_alias.upper()} {'='*20}")
        # 1. Calcula as contagens totais de todas as tags (b, d) para o site
        df_counts = calculate_tag_counts(site_alias, site_file)
        # 2. Calcula a coocorrência (a) e o total de posts da tag principal (c) para o site
        df_a, c = calculate_a_and_c(site_alias)
        # 3. Junta tudo, calcula as heurísticas e filtra
        if not df_a.empty and c > 0 and not df_counts.empty:
            calculate_heuristics_and_filter(df_counts, df_a, c, site_alias)
        else:
            logger.warning(
                f"Não foi possível prosseguir com o cálculo das heurísticas para '{site_alias}' devido a dados ausentes (a, b, c ou d).")

    logger.info("Processo de cálculo de heurísticas de tags finalizado.")


if __name__ == "__main__":
    main()
