from tqdm import tqdm
import json
import pandas as pd
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from s0_prompts import classify_misuse_categories
from s1_make_llm_input import create_llm_input_string
from paths import *


def main():
    """
    Função principal para classificar os tipos de uso indevido de criptografia
    previamente detectados.
    """
    print("Iniciando o processo de classificação de uso indevido...")

    if not os.path.exists(MISUSE_CASES):
        print(
            f"Erro: Arquivo de casos de uso indevido não encontrado em '{MISUSE_CASES}'.")
        print("Execute o script s2_detect_misuse.py primeiro.")
        return

    with open(MISUSE_CASES, 'r', encoding='utf-8') as f:
        misuse_data = json.load(f)

    # Filtra para obter apenas os posts marcados como uso indevido (classification == 1)
    misuse_posts = [post for post in misuse_data if post.get(
        'classification') == 1]
    if not misuse_posts:
        print("Nenhum caso de uso indevido encontrado para classificar.")
        return

    misuse_ids = [post['id'] for post in misuse_posts]
    print(
        f"Encontrados {len(misuse_ids)} casos de uso indevido para classificar.")

    # 2. Carregar todos os posts pré-processados
    if not os.path.exists(PREPROCESSED_POSTS):
        print(
            f"Erro: Arquivo de posts pré-processados não encontrado em '{PREPROCESSED_POSTS}'.")
        return

    print(f"Carregando posts de: {PREPROCESSED_POSTS}")
    df_all_posts = pd.read_csv(PREPROCESSED_POSTS, dtype={'id': str})

    # Filtra o DataFrame para conter apenas os posts que precisamos analisar
    df_to_process = df_all_posts[df_all_posts['id'].isin(misuse_ids)].copy()

    # 3. Configurar o LLM e o prompt para classificação
    llm = ChatOllama(model="llama3.2:3b", temperature=0, format="json")
    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        classify_misuse_categories()
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt_template | llm | parser

    results = []
    print(f"Classificando {len(df_to_process)} posts com o LLM...")

    for _, row in tqdm(df_to_process.iterrows(), total=df_to_process.shape[0], desc="Classificando Usos Indevidos"):
        try:
            post_content = create_llm_input_string(str(row['id']))
            response = chain.invoke({"post": post_content})

            response['id'] = str(row['id'])
            response['site'] = str(row['site'])
            results.append(response)

        except OutputParserException as e:
            print(
                f"Erro de parsing na resposta do LLM para o post ID {row['id']}: {e}")
        except Exception as e:
            print(f"Erro inesperado ao processar o post ID {row['id']}: {e}")

    output_path = CLASSIFIED_MISUSES
    print(
        f"\nProcessamento concluído. {len(results)} classificações foram geradas.")
    print(f"Salvando resultados em: {output_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print("Arquivo de classificações salvo com sucesso!")


if __name__ == "__main__":
    main()
