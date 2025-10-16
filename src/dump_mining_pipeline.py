from dump_mining.s7_preprocess_body import main as run_7_preprocess_body
from dump_mining.s6_filter_posts import main as run_6_filter_posts
from dump_mining.s5_get_connected_posts import main as run_5_get_connected_posts
from dump_mining.s4_get_posts import main as run_4_get_posts
from dump_mining.s3_releated_tags_h2 import main as run_3_releated_tags_h2
from dump_mining.s2_releated_tags_h1 import main as run_2_releated_tags_h1
from dump_mining.s1_get_main_tag import main as run_1_get_main_tag
import sys
import os

# Garante que os módulos no diretório 'src' e 'src/dump_mining' possam ser encontrados
sys.path.append(os.path.abspath(os.path.dirname(__file__)))


def run_full_pipeline():
    """
    Executa todas as etapas do pipeline de mineração de dados em sequência.
    """
    print("--- INICIANDO PIPELINE DE MINERAÇÃO DE DADOS ---")

    print("\n--- ETAPA 1: Extraindo perguntas com a tag principal ---")
    run_1_get_main_tag()

    print("\n--- ETAPA 2: Calculando Heurística 1 (H1) para tags relacionadas ---")
    run_2_releated_tags_h1()

    print("\n--- ETAPA 3: Calculando Heurística 2 (H2) e filtrando tags ---")
    run_3_releated_tags_h2()

    print("\n--- ETAPA 4: Coletando posts completos com base nas tags filtradas ---")
    run_4_get_posts()

    print("\n--- ETAPA 5: Conectando perguntas com suas respectivas respostas ---")
    run_5_get_connected_posts()

    print("\n--- ETAPA 6: Conectando perguntas com suas respectivas respostas ---")
    run_6_filter_posts()

    print("\n--- ETAPA 7: Pré-processando e limpando o corpo dos posts e respostas ---")
    run_7_preprocess_body()

    print("\n--- PIPELINE DE MINERAÇÃO DE DADOS CONCLUÍDO ---")


if __name__ == "__main__":
    run_full_pipeline()
