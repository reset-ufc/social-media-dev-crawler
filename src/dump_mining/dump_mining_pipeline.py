import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_logger
from s7_preprocess_body import main as run_7_preprocess_body
from s6_filter_posts import main as run_6_filter_posts
from s5_get_connected_posts import main as run_5_get_connected_posts
from s4_get_posts import main as run_4_get_posts
from s3_releated_tags_h2 import main as run_3_releated_tags_h2
from s2_releated_tags_h1 import main as run_2_releated_tags_h1
from s1_get_main_tag import main as run_1_get_main_tag


logger = get_logger(__name__)


def run_full_pipeline():
    logger.info("--- INICIANDO PIPELINE DE MINERAÇÃO DE DADOS ---")

    logger.info("\n--- ETAPA 1: Extraindo perguntas com a tag principal ---")
    run_1_get_main_tag()

    logger.info(
        "\n--- ETAPA 2: Calculando Heurística 1 (H1) para tags relacionadas ---")
    run_2_releated_tags_h1()

    logger.info(
        "\n--- ETAPA 3: Calculando Heurística 2 (H2) e filtrando tags ---")
    run_3_releated_tags_h2()

    logger.info(
        "\n--- ETAPA 4: Coletando posts completos com base nas tags filtradas ---")
    run_4_get_posts()

    logger.info(
        "\n--- ETAPA 5: Conectando perguntas com suas respectivas respostas ---")
    run_5_get_connected_posts()

    logger.info("\n--- ETAPA 6: Filtrando posts por popularidade ---")
    run_6_filter_posts()

    logger.info(
        "\n--- ETAPA 7: Pré-processando e limpando o corpo dos posts e respostas ---")
    run_7_preprocess_body()

    logger.info("\n--- PIPELINE DE MINERAÇÃO DE DADOS CONCLUÍDO ---")


if __name__ == "__main__":
    run_full_pipeline()
