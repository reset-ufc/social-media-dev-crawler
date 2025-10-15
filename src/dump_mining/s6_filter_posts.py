
from paths import *
from utils import *
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
    df = pd.read_csv(input_path, dtype=str)
    df_questions = df[df['type'] == 'question'].copy()
    print(
        f"Carregados {len(df)} registros, resultando em {len(df_questions)} perguntas.")

    # Assegurar que as colunas de métrica são numéricas
    metric_cols = ['answer_count', 'view_count', 'score', 'comment_count']
    for col in metric_cols:
        df_questions[col] = pd.to_numeric(
            df_questions[col], errors='coerce').fillna(0)

    # 2. Definir o que é uma questão popular
    quantiles = df_questions[metric_cols].quantile(percentile)
    print(f"Limiares de popularidade (percentil {percentile*100}%):")
    print(quantiles)

    # 3. Filtrar as questões populares
    popular_questions = df_questions[
        (df_questions['answer_count'] >= quantiles['answer_count']) &
        (df_questions['view_count'] >= quantiles['view_count']) &
        (df_questions['score'] >= quantiles['score']) &
        (df_questions['comment_count'] >= quantiles['comment_count'])
    ]
    print(f"Encontradas {len(popular_questions)} questões populares.")

    # Obter os IDs das perguntas populares para filtrar o dataframe original
    popular_ids = popular_questions['id'].unique()
    filtred_posts = df[df['question_id'].isin(
        popular_ids) | df['id'].isin(popular_ids)]

    # 4. Salvar os resultados
    ensure_parent_dir(output_path)
    filtred_posts.to_csv(output_path, index=False)
    print(
        f"\nTotal de {len(filtred_posts)} registros salvos em: {output_path}")

    # 5. Exibir contagem detalhada
    type_counts = filtred_posts['type'].value_counts()
    question_count = type_counts.get('post', 0)
    answer_count = type_counts.get('answer', 0)
    comment_count = type_counts.get('comment', 0)

    print(f"  - Perguntas: {question_count}")
    print(f"  - Respostas: {answer_count}")
    print(f"  - Comentários: {comment_count}")


def main():
    filter_popular_posts(CONNECTED_POSTS, FILTRED_POSTS, percentile=0.90)


if __name__ == "__main__":
    main()
