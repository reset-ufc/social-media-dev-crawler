import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import *
import json
import pandas as pd


def fused_dificulty(df: pd.DataFrame):
    """
    Calculates the fused difficulty for each topic based on the average time to get an accepted answer.
    H_i = T_i / média_global(T)
    """
    # Garante que as colunas de data estão no formato datetime
    try:
        df['creation_date'] = pd.to_datetime(df['creation_date'])
    except KeyError:
        raise ValueError("DataFrame must contain a 'creation_date' column.")
    except Exception as e:
        raise ValueError(f"Could not convert 'creation_date' to datetime: {e}")

    # Separa 'questions' e 'answers'
    questions = df[df['type'] == 'question'].copy()
    answers = df[df['type'] == 'answer'][['question_id','id', 'creation_date']].copy()

    # Filtra questões que possuem uma resposta aceita
    questions_with_accepted = questions[questions['accepted_answer_id'].notna(
    )].copy()

    # Converte accepted_answer_id para tipo numérico para garantir o merge
    questions_with_accepted['accepted_answer_id'] = pd.to_numeric(
        questions_with_accepted['accepted_answer_id'])

    # Renomeia colunas para o merge
    answers.rename(
        columns={'id': 'AnswerId', 'creation_date': 'AnswerCreation_date'}, inplace=True)

    # Junta questões com suas respostas aceitas
    merged_df = pd.merge(
        questions_with_accepted,
        answers,
        left_on='accepted_answer_id',
        right_on='AnswerId',
        how='inner'
    )

    # Calcula o tempo para a resposta em horas
    merged_df['hours_to_accepted_answer'] = (
        merged_df['AnswerCreation_date'] - merged_df['creation_date']).dt.total_seconds() / 3600

    # Agrupa por tópico e calcula a média de horas
    topic_difficulty = (
        merged_df
        .groupby('topic')[['hours_to_accepted_answer']]
        .mean()
        .rename(columns={'hours_to_accepted_answer': 'avg_hours'})
    )

    # Normaliza a métrica
    global_mean_hours = topic_difficulty['avg_hours'].mean()
    topic_difficulty['H_hat'] = topic_difficulty['avg_hours'] / \
        global_mean_hours

    # A "fused_difficulty" é o H_hat normalizado
    topic_difficulty['fused_difficulty'] = topic_difficulty['H_hat']

    result_df = topic_difficulty.reset_index()

    # Retorna apenas colunas relevantes para o merge
    return result_df[['topic', 'fused_difficulty', 'avg_hours']]


def calculate_popularity(df: pd.DataFrame, num_topics: int):
    """
        V̂_i = V_i / média_global(V)
        Ŝ_i = S_i / média_global(S)
        Ĉ_i = C_i / média_global(C)
        P_i = (V̂_i + Ŝ_i + Ĉ_i) / 3
    """

    # Filtra apenas perguntas com tópico atribuído
    questions_df = df[(df['type'] == 'question') &
                      (df['topic'].notna())].copy()

    # Mapeamento de colunas
    metric_cols = {
        'view_count': 'avg_views',
        'score': 'avg_score',
        'comment_count': 'avg_comments'
    }

    # Garante que todas as colunas necessárias existem
    for col in metric_cols.keys():
        if col not in questions_df.columns:
            raise ValueError(f"Missing required metric column: {col}")

    # Agrupa métricas por tópico
    topic_metrics = (
        questions_df
        .groupby('topic')[list(metric_cols.keys())]
        .mean()
        .rename(columns=metric_cols)
    )

    # ======== NORMALIZAÇÃO EXATA DO ARTIGO ========
    # média_global(V), média_global(S), média_global(C)
    global_means = topic_metrics.mean()

    topic_metrics['V_hat'] = topic_metrics['avg_views'] / \
        global_means['avg_views']
    topic_metrics['S_hat'] = topic_metrics['avg_score'] / \
        global_means['avg_score']
    topic_metrics['C_hat'] = topic_metrics['avg_comments'] / \
        global_means['avg_comments']

    # ======== FUSED POPULARITY ========
    topic_metrics['fused_popularity'] = (
        topic_metrics[['V_hat', 'S_hat', 'C_hat']].mean(axis=1)
    )

    # Resultado final conforme esperado
    result_df = topic_metrics.reset_index()

    return result_df


def main():
    """
    Executa o pipeline de cálculo de popularidade e dificuldade fundida.
    """

    # Carrega configuração LDA (de onde vem K)
    if not LDA_CONFIG.exists():
        raise FileNotFoundError(f"LDA config file not found at {LDA_CONFIG}")

    with open(LDA_CONFIG, 'r', encoding='utf-8') as f:
        lda_config = json.load(f)

    num_topics = lda_config.get('num_topics')
    if num_topics is None:
        raise ValueError("'num_topics' (K) missing in LDA config")

    # Carrega dataset de posts classificados
    if not CLASSIFIED_POSTS.exists():
        raise FileNotFoundError(
            f"Classified posts file not found at {CLASSIFIED_POSTS}")

    df = pd.read_csv(CLASSIFIED_POSTS)

    # Calcula métricas de popularidade
    popularity_df = calculate_popularity(df, num_topics)

    # Calcula métricas de dificuldade
    difficulty_df = fused_dificulty(df)

    # Junta os resultados de popularidade e dificuldade
    fused_metrics_df = pd.merge(
        popularity_df, difficulty_df, on='topic', how='outer')

    # Salva CSV final
    FUSED_METRICS.parent.mkdir(parents=True, exist_ok=True)
    fused_metrics_df.to_csv(FUSED_METRICS, index=False)

    print(f"Fused popularity and difficulty metrics saved to {FUSED_METRICS}")
    print(fused_metrics_df.to_string())


if __name__ == '__main__':
    main()
