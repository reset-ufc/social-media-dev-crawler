from paths import *
from utils_global import *
import sys
import os
import subprocess
import xml.etree.ElementTree as ET
import pandas as pd
from itertools import product
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = get_logger(__name__)

TAG_FEATURES = ['tag', 'b', 'a', 'h1', 'h2']

"""
Requisito: Você precisa ter o 7zip instalado no seu sistema operacional
 Linux: sudo apt install p7zip-full.
 Windows: adicione o executável do 7-Zip ao seu PATH.
"""


def initiate_csv(output_path=None):
    """Inicializa um arquivo CSV com as colunas necessárias para tags"""
    if output_path is None:
        output_path = COARSE_QUESTIONS
    ensure_parent_dir(output_path)
    pd.DataFrame(columns=TAG_FEATURES).to_csv(
        output_path,
        index=False,
        encoding="utf-8"
    )


def append_batch(batch_rows, output_path=None):
    """Adiciona um lote de linhas ao CSV"""
    if not batch_rows:
        return
    if output_path is None:
        output_path = COARSE_QUESTIONS
    pd.DataFrame(batch_rows, columns=TAG_FEATURES).to_csv(
        output_path,
        mode="a",
        header=False,
        index=False,
        encoding="utf-8"
    )


def collect_tags_from_7z(site_alias):
    """
    Coleta todas as tags de um site e conta suas ocorrências

    Args:
        site_alias: Alias do site a processar

    Returns:
        Tupla contendo:
        - all_tags_counter: Counter com contagem de todas as tags em todos os posts
        - question_tags_counter: Counter com contagem de tags que co-ocorrem com QUESTION_TAG
    """
    site_file = SITES[site_alias]
    archive_path = os.path.join(DUMP, site_file)

    if not os.path.exists(archive_path):
        logger.warning(
            f"[{site_alias}] Arquivo não encontrado: {archive_path}")
        return Counter(), Counter()

    posts_filename = "Posts.xml"
    all_tags_counter = Counter()  # Todas as tags em todos os posts
    question_tags_counter = Counter()  # Apenas tags que co-ocorrem com QUESTION_TAG

    logger.info(
        f"[{site_alias}] Iniciando coleta de tags do {posts_filename}...")

    with stream_posts_from_7z(archive_path) as context:
        for event, elem in context:
            if elem.tag != "row":
                continue

            if elem.attrib.get("PostTypeId") != "1":
                elem.clear()
                continue

            tags_field = elem.attrib.get("Tags", "")
            if not tags_field:
                elem.clear()
                continue

            tags = extract_tag_list(tags_field)

            # Contar TODAS as tags de todos os posts
            all_tags_counter.update(tags)

            # Verificar se QUESTION_TAG está presente
            if QUESTION_TAG in tags:
                # Contar todas as tags deste post (incluindo QUESTION_TAG)
                question_tags_counter.update(tags)

            elem.clear()

    logger.info(
        f"[{site_alias}] Tags únicas (todos os posts): {len(all_tags_counter)}")
    logger.info(
        f"[{site_alias}] Tags únicas (com {QUESTION_TAG}): {len(question_tags_counter)}")
    return all_tags_counter, question_tags_counter


def calculate_tag_metrics(tag_data):
    """
    Calcula as métricas b, a, h1, h2 para cada tag

    Args:
        tag_data: dict de {site_alias: (all_tags_counter, question_tags_counter)}

    Returns:
        dict com métricas por tag: {tag: {'b': x, 'a': y, 'h1': z, 'h2': w}}
    """
    # Agregar contagens de todas as fontes
    global_all_tags = Counter()  # Todas as tags em todos os sites
    # Tags que co-ocorrem com QUESTION_TAG em todos os sites
    global_question_tags = Counter()

    for all_tags_counter, question_tags_counter in tag_data.values():
        global_all_tags.update(all_tags_counter)
        global_question_tags.update(question_tags_counter)

    # Total de posts com QUESTION_TAG
    total_posts_with_question = global_question_tags.get(QUESTION_TAG, 0)

    if total_posts_with_question == 0:
        logger.warning("Nenhum post com QUESTION_TAG encontrado!")
        return {}

    logger.info(
        f"Total de posts com '{QUESTION_TAG}': {total_posts_with_question}")

    tag_metrics = {}

    for tag in global_question_tags.keys():
        # b: número de posts que contêm a tag (em todos os dados, sem filtro)
        b = global_all_tags.get(tag, 0)

        # a: número de posts que contêm a tag E QUESTION_TAG
        a = global_question_tags.get(tag, 0)

        # h1: a/b (proporção de posts com tag que também têm QUESTION_TAG)
        h1 = a / b if b > 0 else 0

        # h2: a/c (proporção da tag em relação ao total de posts com QUESTION_TAG)
        h2 = a / total_posts_with_question if total_posts_with_question > 0 else 0

        tag_metrics[tag] = {
            'b': b,
            'a': a,
            'h1': h1,
            'h2': h2
        }

    return tag_metrics


def filter_tags_by_thresholds(tag_metrics, threshold1=None, threshold2=None):
    """
    Filtra tags baseado nos thresholds h1 e h2

    Args:
        tag_metrics: dict com métricas por tag
        threshold1: threshold mínimo para h1 (opcional)
        threshold2: threshold mínimo para h2 (opcional)

    Returns:
        dict com tags filtradas
    """
    if threshold1 is None and threshold2 is None:
        return tag_metrics

    filtered = {}

    for tag, metrics in tag_metrics.items():
        passes_h1 = True if threshold1 is None else metrics['h1'] >= threshold1
        passes_h2 = True if threshold2 is None else metrics['h2'] >= threshold2

        if passes_h1 and passes_h2:
            filtered[tag] = metrics

    return filtered


def save_tags_to_csv(tag_metrics, output_path):
    """
    Salva as métricas das tags em um arquivo CSV

    Args:
        tag_metrics: dict com métricas por tag
        output_path: caminho do arquivo de saída
    """
    rows = []
    for tag, metrics in sorted(tag_metrics.items()):
        rows.append([
            tag,
            metrics['b'],
            metrics['a'],
            metrics['h1'],
            metrics['h2']
        ])

    if rows:
        append_batch(rows, output_path)


def process_all_sites(output_path=None, threshold1=None, threshold2=None):
    """
    Processa todos os sites e gera arquivo com tags filtradas

    Args:
        output_path: Caminho do arquivo de saída (opcional)
        threshold1: Threshold para h1 (opcional)
        threshold2: Threshold para h2 (opcional)

    Returns:
        Número de tags que passaram nos filtros
    """
    if output_path is None:
        output_path = COARSE_QUESTIONS

    # Coletar tags de todos os sites
    tag_data = {}
    for site_alias in SITES.keys():
        all_tags_counter, question_tags_counter = collect_tags_from_7z(
            site_alias)
        if all_tags_counter or question_tags_counter:
            tag_data[site_alias] = (all_tags_counter, question_tags_counter)
            logger.info(f"  └─ [{site_alias}] Tags coletadas")

    # Calcular métricas
    logger.info("\nCalculando métricas das tags...")
    tag_metrics = calculate_tag_metrics(tag_data)
    logger.info(f"Total de tags únicas: {len(tag_metrics)}")

    # Aplicar filtros de threshold
    if threshold1 is not None or threshold2 is not None:
        logger.info(
            f"Aplicando filtros: h1 >= {threshold1}, h2 >= {threshold2}")
        tag_metrics = filter_tags_by_thresholds(
            tag_metrics, threshold1, threshold2)
        logger.info(f"Tags após filtragem: {len(tag_metrics)}")

    # Salvar resultados
    initiate_csv(output_path)
    save_tags_to_csv(tag_metrics, output_path)

    return len(tag_metrics)


def test_threshold_combinations():
    """
    Testa várias combinações de thresholds e salva os resultados em arquivos separados
    """
    THRE1 = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    THRE2 = [0.001, 0.002, 0.005, 0.010, 0.015, 0.020, 0.30]

    # Criar diretório para os resultados dos testes
    base_dir = os.path.dirname(COARSE_QUESTIONS)
    threshold_dir = os.path.join(base_dir, "trhs")
    os.makedirs(threshold_dir, exist_ok=True)

    logger.info("=" * 80)
    logger.info("INICIANDO TESTES DE THRESHOLDS")
    logger.info(f"Total de combinações: {len(THRE1) * len(THRE2)}")
    logger.info("=" * 80)

    # Coletar tags de todos os sites UMA VEZ (otimização)
    logger.info("\nColetando tags de todos os sites...")
    tag_data = {}
    for site_alias in SITES.keys():
        all_tags_counter, question_tags_counter = collect_tags_from_7z(
            site_alias)
        if all_tags_counter or question_tags_counter:
            tag_data[site_alias] = (all_tags_counter, question_tags_counter)
            logger.info(f"  └─ [{site_alias}] Tags coletadas")

    # Calcular métricas UMA VEZ
    logger.info("\nCalculando métricas das tags...")
    all_tag_metrics = calculate_tag_metrics(tag_data)
    logger.info(f"Total de tags únicas: {len(all_tag_metrics)}")

    # Gerar todas as combinações de thresholds
    combinations = list(product(THRE1, THRE2))

    # Dicionário para armazenar estatísticas de cada combinação
    combination_stats = {}

    for idx, (thr1, thr2) in enumerate(combinations, 1):
        # Formatar os valores para nomes de arquivo
        thr1_str = f"{thr1:.3f}".replace(".", "_")
        thr2_str = f"{thr2:.3f}".replace(".", "_")

        # Nome do arquivo de saída
        output_filename = f"TRH1_{thr1_str}_TRH2_{thr2_str}.csv"
        output_path = os.path.join(threshold_dir, output_filename)

        logger.info(
            f"\n[{idx}/{len(combinations)}] Processando TRH1={thr1}, TRH2={thr2}")
        logger.info(f"Arquivo: {output_filename}")

        # Filtrar tags com estes thresholds
        filtered_tags = filter_tags_by_thresholds(all_tag_metrics, thr1, thr2)
        num_tags = len(filtered_tags)

        logger.info(f"  └─ Tags que passaram nos filtros: {num_tags}")

        # Salvar resultados
        initiate_csv(output_path)
        save_tags_to_csv(filtered_tags, output_path)

        # Armazenar estatísticas
        combination_key = f"TRH1_{thr1:.3f}_TRH2_{thr2:.3f}"
        combination_stats[combination_key] = {
            'thr1': thr1,
            'thr2': thr2,
            'num_tags': num_tags,
            'tags': sorted(filtered_tags.keys())
        }

        logger.info(f"─" * 60)
        logger.info(f"Tags salvas para TRH1={thr1}, TRH2={thr2}: {num_tags}")
        logger.info(f"─" * 60)

    logger.info("\n" + "=" * 80)
    logger.info("TESTES DE THRESHOLDS CONCLUÍDOS")
    logger.info(f"Arquivos salvos em: {threshold_dir}")
    logger.info("=" * 80)

    # Criar sumarização
    if combination_stats:
        logger.info("\n" + "=" * 80)
        logger.info("SUMARIZAÇÃO DOS RESULTADOS")
        logger.info("=" * 80)

        # Ordenar por número de tags
        sorted_combinations = sorted(
            combination_stats.items(),
            key=lambda x: x[1]['num_tags']
        )

        # Combinação com mais tags
        max_comb = sorted_combinations[-1]
        logger.info(f"\nCOMBINAÇÃO COM MAIS TAGS:")
        logger.info(f"   {max_comb[0]}")
        logger.info(f"   Número de tags: {max_comb[1]['num_tags']}")
        logger.info(
            f"   Thresholds: h1 >= {max_comb[1]['thr1']}, h2 >= {max_comb[1]['thr2']}")

        # Combinação com menos tags
        min_comb = sorted_combinations[0]
        logger.info(f"\nCOMBINAÇÃO COM MENOS TAGS:")
        logger.info(f"   {min_comb[0]}")
        logger.info(f"   Número de tags: {min_comb[1]['num_tags']}")
        logger.info(
            f"   Thresholds: h1 >= {min_comb[1]['thr1']}, h2 >= {min_comb[1]['thr2']}")

        # Combinação mediana
        median_idx = len(sorted_combinations) // 2
        median_comb = sorted_combinations[median_idx]
        logger.info(f"\nCOMBINAÇÃO MEDIANA:")
        logger.info(f"   {median_comb[0]}")
        logger.info(f"   Número de tags: {median_comb[1]['num_tags']}")
        logger.info(
            f"   Thresholds: h1 >= {median_comb[1]['thr1']}, h2 >= {median_comb[1]['thr2']}")

        logger.info("\n" + "=" * 80)

        # Criar arquivo de comparação
        comparison_path = os.path.join(
            threshold_dir, "combinations_comparison.csv")
        logger.info(f"\nCriando arquivo de comparação: {comparison_path}")

        # Encontrar o número máximo de tags para definir o tamanho do DataFrame
        max_tags_length = max(len(stats['tags'])
                              for stats in combination_stats.values())

        # Criar dicionário para o DataFrame
        comparison_data = {}
        for comb_name, stats in sorted(combination_stats.items()):
            # Preencher com tags e completar com strings vazias se necessário
            tags_list = stats['tags'] + [''] * \
                (max_tags_length - len(stats['tags']))
            comparison_data[comb_name] = tags_list

        # Criar e salvar DataFrame
        comparison_df = pd.DataFrame(comparison_data)
        comparison_df.to_csv(comparison_path, index=False, encoding='utf-8')

        logger.info(f"✓ Arquivo de comparação criado com sucesso")
        logger.info(
            f"  Dimensões: {comparison_df.shape[0]} linhas × {comparison_df.shape[1]} colunas")

        # Criar também um arquivo de sumário com estatísticas
        summary_path = os.path.join(threshold_dir, "combinations_summary.csv")
        summary_data = []
        for comb_name, stats in sorted(combination_stats.items()):
            summary_data.append({
                'combination': comb_name,
                'threshold1': stats['thr1'],
                'threshold2': stats['thr2'],
                'num_tags': stats['num_tags']
            })

        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.sort_values('num_tags', ascending=False)
        summary_df.to_csv(summary_path, index=False, encoding='utf-8')

        logger.info(f"✓ Arquivo de sumário criado: {summary_path}")
        logger.info("=" * 80)


def main():
    logger.info("Inicializando processamento de tags com heurísticas...")

    # Gerar arquivo principal sem filtros de threshold
    logger.info("\n### PROCESSAMENTO PRINCIPAL (SEM FILTROS) ###")
    num_tags = process_all_sites()
    logger.info(f"\nTotal de tags salvas no arquivo principal: {num_tags}")

    # Executar testes de threshold
    logger.info("\n### TESTES DE THRESHOLD ###")
    test_threshold_combinations()

    logger.info("\n### PROCESSAMENTO COMPLETO ###")


if __name__ == "__main__":
    main()
