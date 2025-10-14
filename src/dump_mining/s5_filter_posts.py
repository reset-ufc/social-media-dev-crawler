import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from paths import CONNECTED_POSTS, FILTERED_POSTS

# --- Configuração ---
PERCENTILE = 0.90  # top 10%

# --- Carrega os dados ---
print(f"Lendo posts de: {CONNECTED_POSTS}")
df = pd.read_csv(CONNECTED_POSTS)

# Garante que os campos sejam numéricos
for col in ['answer_count', 'view_count', 'score', 'comment_count']:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Calcula o limiar de 90º percentil
metrics = ['answer_count', 'view_count', 'score', 'comment_count']
thresholds = df[df['type'] == 'question'][metrics].quantile(PERCENTILE)
print("\nLimiar por métrica (90º percentil):")
print(thresholds)

# Seleciona perguntas populares
popular_questions = df[
    (df['type'] == 'question') &
    (df['answer_count'] >= thresholds['answer_count']) &
    (df['view_count'] >= thresholds['view_count']) &
    (df['score'] >= thresholds['score']) &
    (df['comment_count'] >= thresholds['comment_count'])
]

# Pega as respostas associadas a essas perguntas
popular_question_ids = popular_questions['id'].unique()
popular_answers = df[
    (df['type'] == 'answer') &
    (df['question_id'].isin(popular_question_ids))
]

# Junta perguntas e respostas filtradas
filtered = pd.concat([popular_questions, popular_answers], ignore_index=True)

# Salva resultado
filtered.to_csv(FILTERED_POSTS, index=False, encoding='utf-8')
print(f"\nFiltro aplicado com sucesso! {len(filtered)} posts salvos em {FILTERED_POSTS}")
