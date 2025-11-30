import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from paths import CONNECTED_POSTS, FILTRED_POSTS
from utils_global import get_logger
import csv


logger = get_logger(__name__)


def filter_popular_posts(input_csv=CONNECTED_POSTS, output_csv=FILTRED_POSTS, percentile=0.75):
    """
    Filtra posts populares (perguntas, respostas e comentários) com base nos percentis
    das métricas answer_count, view_count, score e comment_count.
    """
    logger.info(
        f"Iniciando a filtragem de posts populares do arquivo: {input_csv}")

    try:
        df = pd.read_csv(input_csv, dtype=str)

        before = df.shape[0]
        df.drop_duplicates(inplace=True)
        after = df.shape[0]
        logger.info(f'{before - after} Duplicatas removidas')

    except FileNotFoundError:
        logger.error(f"Arquivo {input_csv} não encontrado.")
        return
    except Exception as e:
        logger.error(f"ERRO ao ler o arquivo {input_csv}: {e}", exc_info=True)
        return

    for col in ['answer_count', 'view_count', 'score', 'comment_count']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

    # Lógica para remover perguntas com apenas uma auto-resposta ---
    logger.info("Verificando perguntas com apenas uma auto-resposta...")
    df['owner_id'] = df['owner_id'].astype(str)
    questions_one_answer = df[(df['type'] == 'question') & (df['answer_count'] == 1)].copy()

    if not questions_one_answer.empty:
        # 2. Isola todas as respostas
        answers = df[df['type'] == 'answer'].copy()

        # 3. Junta as perguntas de uma resposta com suas respectivas respostas
        merged = pd.merge(
            questions_one_answer[['id', 'owner_id']],
            answers[['question_id', 'owner_id']],
            left_on='id',
            right_on='question_id',
            suffixes=('_q', '_a')
        )

        # 4. Identifica os IDs das perguntas onde o autor é o mesmo
        self_answered_ids = set(merged[merged['owner_id_q'] == merged['owner_id_a']]['id'])

        if self_answered_ids:
            logger.info(f"Encontradas e removidas {len(self_answered_ids)} perguntas que continham apenas uma auto-resposta.")
            # 5. Remove todos os posts (perguntas, respostas, comentários) relacionados a esses IDs
            df = df[~df['question_id'].isin(self_answered_ids)]
    # --- Fim da lógica de remoção ---

    df_questions = df[df['type'] == 'question'].copy()
    logger.info(f"Encontradas {len(df_questions)} perguntas no total.")

    # Garante que todas as colunas numéricas existem
    for col in ['answer_count', 'view_count', 'score', 'comment_count']:
        if col not in df_questions.columns:
            df_questions[col] = 0

    if df_questions.empty:
        logger.warning("Nenhuma pergunta encontrada.")
        return

    questions_q = df_questions[[
        'answer_count', 'view_count', 'score', 'comment_count']].quantile(percentile)
    logger.info(f"Limiares de popularidade (percentil {percentile*100}%):")
    logger.info(f"\n{questions_q.to_string()}")

    # Filtra perguntas populares
    popular_questions = df_questions[
        (df_questions['answer_count'] >= questions_q['answer_count']) &
        (df_questions['view_count'] >= questions_q['view_count']) &
        (df_questions['score'] >= questions_q['score']) &
        (df_questions['comment_count'] >= questions_q['comment_count'])
    ]

    logger.info(f"Encontradas {len(popular_questions)} questões populares.\n")

    if popular_questions.empty:
        logger.warning("Nenhuma questão atende aos critérios de popularidade.")
        return

    popular_ids = set(popular_questions['question_id']).union(
        set(popular_questions['id']))

    popular_related = df[df['question_id'].isin(
        popular_ids) | df['id'].isin(popular_ids)]

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    popular_related.to_csv(output_csv, index=False, quoting=csv.QUOTE_MINIMAL)

    logger.info(
        f"Total de {len(popular_related)} registros salvos em: {output_csv}")
    logger.info(
        f"  - Perguntas: {(popular_related['type'] == 'question').sum()}")
    logger.info(
        f"  - Respostas: {(popular_related['type'] == 'answer').sum()}")
    logger.info(
        f"  - Comentários: {(popular_related['type'] == 'comment').sum()}")

    questions_saved = popular_related[popular_related['type'] == 'question']
    site_counts = questions_saved['site_alias'].value_counts()

    logger.info("\nContagem de perguntas salvas por site:")
    for site, count in site_counts.items():
        logger.info(f"  - {site}: {count} perguntas")


def main():
    """Função principal usada pelo pipeline"""
    logger.info("--- ETAPA 6: Filtrando posts populares ---")
    filter_popular_posts(CONNECTED_POSTS, FILTRED_POSTS, percentile=0.75)
    logger.info("=== Etapa 6 concluída com sucesso ===")


if __name__ == "__main__":
    main()
