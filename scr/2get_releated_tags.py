import pandas as pd
from config import *

def make_releated_tags():
    """
    Lê o arquivo CSV de perguntas, extrai todas as tags, conta a ocorrência de cada uma
    e salva o resultado em um novo arquivo CSV.
    """
    try:
        df_coarse = pd.read_csv(QUESTIONS_CSV)
    except FileNotFoundError:
        print(f"ERRO: Arquivo de perguntas não encontrado: {QUESTIONS_CSV}.")
        return

    if 'tags' not in df_coarse.columns:
        print(f"ERRO: Coluna 'tags' não encontrada em {QUESTIONS_CSV}.")
        return

    # Remove linhas onde a coluna 'tags' está vazia ou é nula
    df_coarse.dropna(subset=['tags'], inplace=True)

    # A mágica acontece aqui: divide as strings de tags e expande para que cada tag tenha sua própria linha
    explode_tags = df_coarse['tags'].str.split(';').explode()

    # Conta a frequência de cada tag
    tag_counts_series = explode_tags.value_counts()

    # Converte a série em um DataFrame e nomeia as colunas
    releated_tags_df = tag_counts_series.reset_index()
    releated_tags_df.columns = ['tag', 'ocorr']

    # Filtra a tag principal da análise, se existir
    if QUESTION_TAG in releated_tags_df['tag'].values:
        releated_tags_df = releated_tags_df[releated_tags_df['tag'] != QUESTION_TAG]

    # Salva o resultado em um arquivo CSV
    releated_tags_df.to_csv(RELEATED_TAGS, index=False)
    print(f"Arquivo de tags relacionadas salvo em: {RELEATED_TAGS}")

if __name__ == "__main__":
    make_releated_tags()