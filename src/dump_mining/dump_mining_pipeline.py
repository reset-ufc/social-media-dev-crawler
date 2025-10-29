import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from s1_get_main_tag import main as run_1_get_main_tag
from s2_calculate_tag_heuristics import main as run_2_calculate_tag_heuristics
from s4_get_posts import main as run_4_get_posts
from s5_get_connected_posts import main as run_5_get_connected_posts
from s6_filter_posts import main as run_6_filter_posts
from s7_preprocess_body import main as run_7_preprocess_body
from utils_global import get_logger
from paths import DUMP_MINING_LOG_FILE
from utils_global import ensure_parent_dir


logger = get_logger(__name__)

def clear_log_file():
    """Limpa o arquivo de log antes de uma nova execução."""
    ensure_parent_dir(DUMP_MINING_LOG_FILE)
    with open(DUMP_MINING_LOG_FILE, 'w') as f:
        f.write('')


def run_full_pipeline():
    clear_log_file()
    logger.info("##### INICIANDO PIPELINE DE MINERAÇÃO DE DADOS #####")

    logger.info("\n=== ETAPA 1: Extraindo perguntas com a tag principal ===")
    run_1_get_main_tag()

    logger.info(
        "\n=== ETAPA 2 & 3: Calculando Heurísticas (H1, H2) e filtrando tags por site ===")
    run_2_calculate_tag_heuristics()

    logger.info(
        "\n=== ETAPA 4: Coletando posts completos com base nas tags filtradas ===")
    run_4_get_posts()

    logger.info(
        "\n=== ETAPA 5: Conectando perguntas com suas respectivas respostas ===")
    run_5_get_connected_posts()

    logger.info("\n=== ETAPA 6: Filtrando posts por popularidade ===")
    run_6_filter_posts()

    logger.info(
        "\n=== ETAPA 7: Limpando body e validando trexos de código ===")
    run_7_preprocess_body()

    logger.info("\n##### PIPELINE DE MINERAÇÃO DE DADOS CONCLUÍDO #####")


if __name__ == "__main__":
    run_full_pipeline()
