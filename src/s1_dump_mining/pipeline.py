import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from s1_get_main_tag import main as run_1_get_main_tag
from s2_calculate_tag_heuristics import main as run_2_calculate_tag_heuristics
from s3_get_full_posts import main as run_4_get_posts
from s4_filter_posts import main as run_6_filter_posts
from utils_global import get_logger
from paths import DUMP_MINING_LOG_FILE
from utils_global import ensure_parent_dir, count_posts_comments_in_dumps


logger = get_logger('dump_mining_pipeline')

def clear_log_file():
    """Limpa o arquivo de log antes de uma nova execução."""
    ensure_parent_dir(DUMP_MINING_LOG_FILE)
    with open(DUMP_MINING_LOG_FILE, 'w') as f:
        f.write('')


def run_full_pipeline():
    clear_log_file()
    logger.info("##### INICIANDO PIPELINE DE MINERAÇÃO DE DADOS #####")

    logger.info('Contando total de posts nos dumps')
    count_posts_comments_in_dumps()

    logger.info("\n=== ETAPA 1: Extraindo perguntas com a tag principal ===")
    run_1_get_main_tag()

    logger.info(
        "\n=== ETAPA 2: Calculando Heurísticas (H1, H2) e filtrando tags por site ===")
    run_2_calculate_tag_heuristics()

    logger.info(
        "\n=== ETAPA 3: Coletando posts completos com base nas tags filtradas ===")
    run_4_get_posts()

    logger.info("\n=== ETAPA 4: Filtrando posts por popularidade ===")
    run_6_filter_posts()

    logger.info("\n##### PIPELINE DE MINERAÇÃO DE DADOS CONCLUÍDO #####")


if __name__ == "__main__":
    run_full_pipeline()
