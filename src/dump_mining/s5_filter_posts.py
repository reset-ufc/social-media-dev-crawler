import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import *
from utils import *

def filter_popular_posts(input_path, output_path, percentile=0.90):
    """
    Filtra as perguntas mais populares de um arquivo CSV.

    A popularidade é definida com base em um percentil de contagem de respostas, visualizações e pontuação.

    Args: 
        input_path (Path): Caminho para o arquivo CSV de entrada (RELEATED_POSTS).
        output_path (Path): Caminho para salvar o arquivo CSV de saída (FILTRED_POSTS).
        percentile (float): O percentil para definir o limiar de popularidade.
    """
    print(f"Iniciando a filtragem de posts populares do arquivo: {input_path}")

    if not input_path.exists():
        print(f"Erro: Arquivo de entrada não encontrado em '{input_path}'")
        return

    # 1. Carregar os posts relacionados
    df = pd.read_csv(input_path)
    print(f"Carregadas {len(df)} perguntas.")

    # 2. Definir o que é uma questão popular
    # Assumindo que todos os registros no arquivo de entrada são perguntas.
    quantiles = df[['answer_count', 'view_count', 'score']
                   ].quantile(percentile)
    print(f"Limiares de popularidade (percentil {percentile*100}%):")
    print(quantiles)

    # 3. Filtrar as questões populares
    filtred_posts = df[
        (df['answer_count'] >= quantiles['answer_count']) &
        (df['view_count'] >= quantiles['view_count']) &
        (df['score'] >= quantiles['score'])
    ]
    print(f"Encontradas {len(filtred_posts)} questões populares.")

    # 4. Salvar os resultados
    ensure_parent_dir(output_path)
    filtred_posts.to_csv(output_path, index=False)
    print(
        f"\n{len(filtred_posts)} posts e respostas filtrados foram salvos em: {output_path}")


if __name__ == "__main__":
    filter_popular_posts(RELEATED_POSTS, FILTRED_POSTS, percentile=0.90)
