import sys
import os
import subprocess  
import xml.etree.ElementTree as ET
import pandas as pd
from itertools import product

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils_global import *
from paths import *

logger = get_logger(__name__)

QUESTION_FEATURES = ['site', 'tags', 'question_id']

"""
Requisito: Você precisa ter o 7zip instalado no seu sistema operacional
 Linux: sudo apt install p7zip-full.
 Windows: adicione o executável do 7-Zip ao seu PATH.
"""


def initiate_csv(output_path=None):
    """Inicializa um arquivo CSV com as colunas necessárias"""
    if output_path is None:
        output_path = COARSE_QUESTIONS
    ensure_parent_dir(output_path)
    pd.DataFrame(columns=QUESTION_FEATURES).to_csv(
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
    pd.DataFrame(batch_rows, columns=QUESTION_FEATURES).to_csv(
        output_path,
        mode="a",
        header=False,
        index=False,
        encoding="utf-8"
    )


def parse_posts_from_7z(site_alias, output_path=None, threshold1=None, threshold2=None):
    """
    Processa posts de um arquivo 7z e filtra baseado em thresholds opcionais
    
    Args:
        site_alias: Alias do site a processar
        output_path: Caminho do arquivo de saída (opcional)
        threshold1: Primeiro threshold para filtragem (opcional)
        threshold2: Segundo threshold para filtragem (opcional)
    
    Returns:
        Número de posts processados
    """
    site_file = SITES[site_alias]
    archive_path = os.path.join(DUMP, site_file)

    if not os.path.exists(archive_path):
        logger.warning(f"[{site_alias}] Arquivo não encontrado: {archive_path}")
        return 0

    posts_filename = "Posts.xml"
    post_count = 0
    
    logger.info(f"[{site_alias}] Iniciando Streaming do {posts_filename} via Pipe...")

    batch = []
    batch_size = 1000

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
            if QUESTION_TAG not in tags:
                elem.clear()
                continue

            # Aplicar filtros de threshold se fornecidos
            if threshold1 is not None or threshold2 is not None:
                # Aqui você pode adicionar a lógica de filtragem baseada nos thresholds
                # Por exemplo, filtrar com base em alguma pontuação ou métrica
                # Esta parte depende da sua lógica específica de negócio
                pass

            post_count += 1
            batch.append([
                site_alias,
                ";".join(tags),
                elem.attrib.get("Id", ""),
            ])

            if len(batch) >= batch_size:
                append_batch(batch, output_path)
                batch.clear()

            elem.clear()

    append_batch(batch, output_path)

    logger.info(f"[{site_alias}] Concluído. Posts salvos: {post_count}")
    return post_count


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
    
    # Gerar todas as combinações de thresholds
    combinations = list(product(THRE1, THRE2))
    
    # Dicionário para armazenar estatísticas de cada combinação
    combination_stats = {}
    
    for idx, (thr1, thr2) in enumerate(combinations, 1):
        # Formatar os valores para nomes de arquivo (substituir ponto por underscore se necessário)
        thr1_str = f"{thr1:.3f}".replace(".", "_")
        thr2_str = f"{thr2:.3f}".replace(".", "_")
        
        # Nome do arquivo de saída
        output_filename = f"TRH1_{thr1_str}_TRH2_{thr2_str}.csv"
        output_path = os.path.join(threshold_dir, output_filename)
        
        logger.info(f"\n[{idx}/{len(combinations)}] Processando TRH1={thr1}, TRH2={thr2}")
        logger.info(f"Arquivo: {output_filename}")
        
        # Inicializar CSV para esta combinação
        initiate_csv(output_path)
        
        # Processar todos os sites com estes thresholds
        total_posts = 0
        for site_alias in SITES.keys():
            posts = parse_posts_from_7z(
                site_alias, 
                output_path=output_path,
                threshold1=thr1,
                threshold2=thr2
            )
            total_posts += posts
        
        logger.info(f"Total de posts para TRH1={thr1}, TRH2={thr2}: {total_posts}")
        
        # Coletar tags únicas desta combinação
        try:
            df = pd.read_csv(output_path)
            all_tags = set()
            for tags_str in df['tags'].dropna():
                tags = tags_str.split(';')
                all_tags.update(tags)
            
            num_unique_tags = len(all_tags)
            combination_key = f"TRH1_{thr1:.3f}_TRH2_{thr2:.3f}"
            combination_stats[combination_key] = {
                'thr1': thr1,
                'thr2': thr2,
                'num_tags': num_unique_tags,
                'tags': sorted(all_tags),
                'total_posts': total_posts
            }
            
            logger.info(f"Tags únicas: {num_unique_tags}")
        except Exception as e:
            logger.error(f"Erro ao processar tags: {e}")
    
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
        logger.info(f"\n🔝 COMBINAÇÃO COM MAIS TAGS:")
        logger.info(f"   {max_comb[0]}")
        logger.info(f"   Número de tags: {max_comb[1]['num_tags']}")
        logger.info(f"   Total de posts: {max_comb[1]['total_posts']}")
        
        # Combinação com menos tags
        min_comb = sorted_combinations[0]
        logger.info(f"\n🔻 COMBINAÇÃO COM MENOS TAGS:")
        logger.info(f"   {min_comb[0]}")
        logger.info(f"   Número de tags: {min_comb[1]['num_tags']}")
        logger.info(f"   Total de posts: {min_comb[1]['total_posts']}")
        
        # Combinação mediana
        median_idx = len(sorted_combinations) // 2
        median_comb = sorted_combinations[median_idx]
        logger.info(f"\n📊 COMBINAÇÃO MEDIANA:")
        logger.info(f"   {median_comb[0]}")
        logger.info(f"   Número de tags: {median_comb[1]['num_tags']}")
        logger.info(f"   Total de posts: {median_comb[1]['total_posts']}")
        
        logger.info("\n" + "=" * 80)
        
        # Criar arquivo de comparação
        comparison_path = os.path.join(threshold_dir, "combinations_comparison.csv")
        logger.info(f"\nCriando arquivo de comparação: {comparison_path}")
        
        # Encontrar o número máximo de tags para definir o tamanho do DataFrame
        max_tags_length = max(len(stats['tags']) for stats in combination_stats.values())
        
        # Criar dicionário para o DataFrame
        comparison_data = {}
        for comb_name, stats in sorted(combination_stats.items()):
            # Preencher com tags e completar com NaN se necessário
            tags_list = stats['tags'] + [''] * (max_tags_length - len(stats['tags']))
            comparison_data[comb_name] = tags_list
        
        # Criar e salvar DataFrame
        comparison_df = pd.DataFrame(comparison_data)
        comparison_df.to_csv(comparison_path, index=False, encoding='utf-8')
        
        logger.info(f"✓ Arquivo de comparação criado com sucesso")
        logger.info(f"  Dimensões: {comparison_df.shape[0]} linhas × {comparison_df.shape[1]} colunas")
        
        # Criar também um arquivo de sumário com estatísticas
        summary_path = os.path.join(threshold_dir, "combinations_summary.csv")
        summary_data = []
        for comb_name, stats in sorted(combination_stats.items()):
            summary_data.append({
                'combination': comb_name,
                'threshold1': stats['thr1'],
                'threshold2': stats['thr2'],
                'num_unique_tags': stats['num_tags'],
                'total_posts': stats['total_posts']
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.sort_values('num_unique_tags', ascending=False)
        summary_df.to_csv(summary_path, index=False, encoding='utf-8')
        
        logger.info(f"✓ Arquivo de sumário criado: {summary_path}")
        logger.info("=" * 80)


def main():
    logger.info("Inicializando coleta otimizada (Zero-Disk-Usage)...")
    
    # Gerar arquivo principal com thresholds padrão
    logger.info("\n### PROCESSAMENTO PRINCIPAL ###")
    initiate_csv()
    for site_alias in SITES.keys():
        parse_posts_from_7z(site_alias)
    
    # Executar testes de threshold
    logger.info("\n### TESTES DE THRESHOLD ###")
    test_threshold_combinations()
    
    logger.info("\n### PROCESSAMENTO COMPLETO ###")


if __name__ == "__main__":
    main()