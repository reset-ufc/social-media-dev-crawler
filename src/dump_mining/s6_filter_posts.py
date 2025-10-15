import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from paths import CONNECTED_POSTS, FILTRED_POSTS
import csv


def filter_popular_posts(input_csv=CONNECTED_POSTS, output_csv=FILTRED_POSTS, percentile=0.90):
    """
    Filtra posts populares (perguntas, respostas e comentários) com base nos percentis
    das métricas answer_count, view_count, score e comment_count.
    """
    print(f"Iniciando a filtragem de posts populares do arquivo: {input_csv}")

    try:
        df = pd.read_csv(input_csv, dtype=str)
    except FileNotFoundError:
        print(f"ERRO: Arquivo {input_csv} não encontrado.")
        return
    except Exception as e:
        print(f"ERRO ao ler o arquivo {input_csv}: {e}")
        return

    # Converte colunas numéricas
    for col in ['answer_count', 'view_count', 'score', 'comment_count']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

    # Seleciona apenas perguntas
    df_questions = df[df['type'] == 'question'].copy()

    # Garante que todas as colunas numéricas existem
    for col in ['answer_count', 'view_count', 'score', 'comment_count']:
        if col not in df_questions.columns:
            df_questions[col] = 0

    print(f"Carregados {len(df)} registros, resultando em {len(df_questions)} perguntas.")

    if df_questions.empty:
        print("Nenhuma pergunta encontrada.")
        return

    # Calcula o percentil 90 para cada métrica
    questions_q = df_questions[['answer_count', 'view_count', 'score', 'comment_count']].quantile(percentile)
    print("Limiares de popularidade (percentil 90.0%):")
    print(questions_q)

    # Filtra perguntas populares
    popular_questions = df_questions[
        (df_questions['answer_count'] >= questions_q['answer_count']) &
        (df_questions['view_count'] >= questions_q['view_count']) &
        (df_questions['score'] >= questions_q['score']) &
        (df_questions['comment_count'] >= questions_q['comment_count'])
    ]

    print(f"Encontradas {len(popular_questions)} questões populares.\n")

    if popular_questions.empty:
        print("Nenhuma questão atende aos critérios de popularidade.")
        return

    # Coleta IDs de perguntas populares
    popular_ids = set(popular_questions['question_id']).union(set(popular_questions['id']))

    # Adiciona respostas e comentários vinculados
    popular_related = df[df['question_id'].isin(popular_ids) | df['id'].isin(popular_ids)]

    # Salva resultado final
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    popular_related.to_csv(output_csv, index=False, quoting=csv.QUOTE_MINIMAL)

    print(f"Total de {len(popular_related)} registros salvos em: {output_csv}")
    print(f"  - Perguntas: {(popular_related['type'] == 'question').sum()}")
    print(f"  - Respostas: {(popular_related['type'] == 'answer').sum()}")
    print(f"  - Comentários: {(popular_related['type'] == 'comment').sum()}")


def main():
    """Função principal usada pelo pipeline"""
    print("--- ETAPA 6: Filtrando posts populares ---")
    filter_popular_posts(CONNECTED_POSTS, FILTRED_POSTS, percentile=0.90)
    print("=== Etapa 6 concluída com sucesso ===")


if __name__ == "__main__":
    main()
