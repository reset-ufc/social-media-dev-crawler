import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import *
import json
import pandas as pd


def fused_dificulty(df: pd.DataFrame):
    """
    Calcula métricas de dificuldade e retorna:
      topic,
      avg_hours,                # média de horas até resposta aceita (por tópico)
      avg_no_acpt_answer,       # proporção de perguntas sem accepted_answer_id (por tópico)
      T_hat,                    # avg_hours / média_global(avg_hours)
      P_hat,                    # avg_no_acpt_answer / média_global(avg_no_acpt_answer)
      fused_dificulty           # (P_hat + T_hat) / 2
    ---------------------------------------------------------------
    Observações:
    - Para tópicos sem nenhuma pergunta com resposta aceita, avg_hours é preenchido
      com a média global de avg_hours antes de calcular T_hat (neutraliza T_hat = 1).
    - As datas são convertidas com errors='coerce' para evitar crashes por formatos inválidos.
    """

    # checagens iniciais
    if 'creation_date' not in df.columns:
        raise ValueError("DataFrame must contain 'creation_date' column.")
    if 'type' not in df.columns:
        raise ValueError("DataFrame must contain 'type' column.")
    if 'topic' not in df.columns:
        raise ValueError("DataFrame must contain 'topic' column.")
    # accepted_answer_id pode não existir em todos os datasets, mas a função espera que exista:
    if 'accepted_answer_id' not in df.columns:
        df['accepted_answer_id'] = pd.NA

    # garantir formatos
    df['creation_date'] = pd.to_datetime(df['creation_date'], errors='coerce')
    df['accepted_answer_id'] = pd.to_numeric(df['accepted_answer_id'], errors='coerce')

    # preparar answers (e converter data de criação das respostas)
    answers = df[df['type'] == 'answer'][['question_id', 'id', 'creation_date']].copy()
    answers['creation_date'] = pd.to_datetime(answers['creation_date'], errors='coerce')
    answers.rename(columns={'id': 'AnswerId', 'creation_date': 'answer_creation_date'}, inplace=True)

    # perguntas
    questions = df[df['type'] == 'question'].copy()

    # -------------------------
    # 1) Média de horas até resposta aceita (avg_hours)
    # -------------------------
    # perguntas que têm accepted_answer_id
    questions_with_accepted = questions[questions['accepted_answer_id'].notna()].copy()
    # merge com respostas para obter timestamp da resposta aceita
    merged = pd.merge(
        questions_with_accepted,
        answers,
        left_on='accepted_answer_id',
        right_on='AnswerId',
        how='inner'
    )

    # calcular delta em horas
    merged['hours_to_accepted_answer'] = (
        merged['answer_creation_date'] - merged['creation_date']
    ).dt.total_seconds() / 3600

    # filtrar casos inválidos
    merged = merged[merged['hours_to_accepted_answer'].notna() & (merged['hours_to_accepted_answer'] >= 0)]

    # média por tópico (apenas tópicos que têm accepted answers aqui)
    topic_avg_hours = (
        merged.groupby('topic', as_index=True)['hours_to_accepted_answer']
        .mean()
        .rename('avg_hours')
        .to_frame()
    )

    # -------------------------
    # 2) Proporção de perguntas sem accepted answer (avg_no_acpt_answer)
    # -------------------------
    total_q_by_topic = questions.groupby('topic').size().rename('total_q')
    no_acc_by_topic = questions[questions['accepted_answer_id'].isna()].groupby('topic').size().rename('no_acc_q')

    not_acc_df = pd.concat([total_q_by_topic, no_acc_by_topic], axis=1).fillna(0)
    not_acc_df['avg_no_acpt_answer'] = not_acc_df['no_acc_q'] / not_acc_df['total_q']
    not_acc_df = not_acc_df[['avg_no_acpt_answer']]

    # -------------------------
    # 3) Unir tópicos (garantir que todos os tópicos apareçam)
    # -------------------------
    all_topics = pd.Index(sorted(set(list(topic_avg_hours.index) + list(not_acc_df.index))))
    base_df = pd.DataFrame(index=all_topics)

    base_df = base_df.join(topic_avg_hours, how='left')
    base_df = base_df.join(not_acc_df, how='left')

    # -------------------------
    # 4) Preencher avg_hours faltante com média global (neutralizar T_hat = 1)
    # -------------------------
    # calcular média global apenas com os tópicos que têm avg_hours
    if base_df['avg_hours'].notna().any():
        global_mean_hours = base_df['avg_hours'].mean(skipna=True)
    else:
        # se nenhum tópico tem avg_hours (caso extremo), definir 1 hora para evitar divisão por zero
        global_mean_hours = 1.0

    # preenche avg_hours faltante com a média global calculada
    base_df['avg_hours'] = base_df['avg_hours'].fillna(global_mean_hours)

    # -------------------------
    # 5) Normalizações (T_hat e P_hat)
    # -------------------------
    # T_hat: avg_hours / média_global(avg_hours)
    # já temos global_mean_hours
    # proteger contra divisão por zero
    if global_mean_hours == 0:
        base_df['T_hat'] = 0.0
    else:
        base_df['T_hat'] = base_df['avg_hours'] / global_mean_hours

    # P_hat: normalizar avg_no_acpt_answer pela média global de avg_no_acpt_answer
    # Se algumas linhas tiverem NaN em avg_no_acpt_answer (tópicos sem perguntas), tratar como 0
    base_df['avg_no_acpt_answer'] = base_df['avg_no_acpt_answer'].fillna(0.0)
    global_mean_no_acc = base_df['avg_no_acpt_answer'].mean()
    if global_mean_no_acc == 0:
        # se média global for zero (nenhum tópico tem perguntas sem accepted), set P_hat = 0
        base_df['P_hat'] = 0.0
    else:
        base_df['P_hat'] = base_df['avg_no_acpt_answer'] / global_mean_no_acc

    # -------------------------
    # 6) fused_dificulty = (P_hat + T_hat) / 2
    # -------------------------
    base_df['fused_dificulty'] = (base_df['P_hat'] + base_df['T_hat']) / 2

    # -------------------------
    # 7) organizar colunas e retornar
    # -------------------------
    result = base_df.reset_index().rename(columns={'index': 'topic'})
    # garantir ordem pedida:
    # avg_hours, avg_no_acpt_answer, T_hat, P_hat, fused_dificulty
    result = result[['topic', 'avg_hours', 'avg_no_acpt_answer', 'T_hat', 'P_hat', 'fused_dificulty']]

    return result



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
