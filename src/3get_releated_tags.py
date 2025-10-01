import pandas as pd
import os
from config import *

def calculate_c():
    """
    Calcula c = número total de perguntas no QUESTIONS_CSV que contêm QUESTION_TAG.
    Retorna um inteiro (0 se não puder calcular).
    """
    print("Calculando a constante 'c' (nº de perguntas que contêm a tag principal)...")
    try:
        df_q = pd.read_csv(QUESTIONS_CSV, dtype={'tags': str})
    except FileNotFoundError:
        print(f"ERRO: arquivo não encontrado: {QUESTIONS_CSV}")
        return 0

    if 'tags' not in df_q.columns:
        print(f"ERRO: coluna 'tags' não encontrada em {QUESTIONS_CSV}")
        return 0

    # Garantir string e sem NaN
    df_q['tags'] = df_q['tags'].fillna('')

    # Procuramos a tag principal como token (ex.: tags separadas por ';')
    # padrão: (^|;)TAG(;|$) - insensível a maiúsculas/minúsculas
    pattern = rf'(^|;)\s*{QUESTION_TAG}\s*(;|$)'
    contains_main = df_q['tags'].str.contains(pattern, case=False, na=False, regex=True)
    c = int(contains_main.sum())
    print(f"Constante c = {c}")
    return c


def calculate_h2():
    """
    Lê RELEATED_TAGS (deve conter coluna 'a'), calcula h2 = a / c e grava o mesmo arquivo
    com a coluna 'h2' adicionada (substitui/atualiza RELEATED_TAGS).
    """
    print("Calculando h2 = a / c ...")
    if not os.path.exists(RELEATED_TAGS):
        print(f"ERRO: arquivo {RELEATED_TAGS} não encontrado. Execute make_releated_tags() (H1) primeiro.")
        return

    df = pd.read_csv(RELEATED_TAGS)

    if 'a' not in df.columns:
        print("ERRO: coluna 'a' não encontrada em RELEATED_TAGS. Execute make_releated_tags() primeiro.")
        return

    # garantir que 'a' seja numérico
    df['a'] = pd.to_numeric(df['a'], errors='coerce').fillna(0).astype(int)

    c = calculate_c()
    if c <= 0:
        print("ERRO: valor de c inválido (0). Não é possível calcular h2.")
        return

    df['h2'] = (df['a'] / c).fillna(0)

    df.to_csv(RELEATED_TAGS, index=False)
    print(f"Coluna 'h2' adicionada e arquivo salvo em: {RELEATED_TAGS}")


def filter_by_h2_threshold():
    """
    Filtra RELEATED_TAGS removendo tags onde h2 < THRE2 e grava o resultado (substitui o CSV).
    """
    print(f"Filtrando tags com h2 < {THRE2} ...")
    if not os.path.exists(RELEATED_TAGS):
        print(f"ERRO: arquivo {RELEATED_TAGS} não encontrado.")
        return

    df = pd.read_csv(RELEATED_TAGS)

    if 'h2' not in df.columns:
        print("ERRO: coluna 'h2' não encontrada. Execute calculate_h2() primeiro.")
        return

    original = len(df)
    df = df[df['h2'] >= THRE2].reset_index(drop=True)
    removed = original - len(df)

    df.to_csv(RELEATED_TAGS, index=False)
    print(f"Filtro aplicado: {removed} tags removidas. Arquivo atualizado: {RELEATED_TAGS}")


if __name__ == "__main__":
    calculate_h2()
    filter_by_h2_threshold()
