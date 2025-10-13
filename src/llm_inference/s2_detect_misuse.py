from s1_make_llm_input import create_llm_input_string
from s0_prompts import detect_misuse

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

from paths import *


def test_on_sample():
    """
    Executa o processo de detecção nos 10 primeiros posts do dataset
    e salva o resultado em 'rq1_test.json'.
    """
    print("--- MODO DE TESTE: Executando nos 10 primeiros posts do dataset ---")

    input_path = PREPROCESSED_POSTS
    if not os.path.exists(input_path):
        print(f"Erro: Arquivo de entrada não encontrado em '{input_path}'.")
        return

    output_path = os.path.join(os.path.dirname(MISUSE_CASES), 'rq1_test.json')

    df = pd.read_csv(input_path)
    if df.empty:
        print("Arquivo de entrada está vazio.")
        return

    # Pega os 10 primeiros posts
    sample_df = df.head(10)

    llm = ChatOllama(model="llama3.2:3b", temperature=0, format="json")
    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        detect_misuse()
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt_template | llm | parser

    results = []
    print(f"Processando {len(sample_df)} posts para o teste...")

    for _, row in tqdm(sample_df.iterrows(), total=sample_df.shape[0], desc="Analisando Posts de Teste"):
        try:
            post_content = create_llm_input_string(str(row['id']))
            response = chain.invoke({"post": post_content})
            # Adiciona o ID e o nome do site à resposta antes de salvá-la
            response['id'] = str(row['id'])
            response['site'] = str(row['site']) # Assumindo que a coluna 'site' existe no DataFrame
            results.append(response)
        except Exception as e:
            print(f"Erro ao processar o post de teste ID {row['id']}: {e}")

    print(
        f"\nProcessamento de teste concluído. {len(results)} resultados foram gerados.")
    print(f"Salvando resultados em: {output_path}")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        print("Arquivo de teste salvo com sucesso!")
    except Exception as e:
        print(f"Erro ao salvar o arquivo JSON de teste: {e}")
    print("\n--- FIM DO MODO DE TESTE ---")


def main():
    """
    Função principal para processar posts, detectar usos indevidos de criptografia
    e salvar os resultados.
    """
    print("Iniciando o processo de detecção de uso indevido de criptografia...")

    input_path = PREPROCESSED_POSTS
    if not os.path.exists(input_path):
        print(f"Erro: Arquivo de entrada não encontrado em '{input_path}'.")
        return

    print(f"Carregando posts de: {input_path}")
    df = pd.read_csv(input_path)

    llm = ChatOllama(model="gemma3:1b", temperature=0, format="json")

    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        detect_misuse()
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt_template | llm | parser

    results = []
    print(
        f"Processando {len(df)} posts com o LLM. Isso pode levar um tempo...")

    for _, row in tqdm(df.iterrows(), total=df.shape[0], desc="Analisando Posts"):
        try:
            # Usa a função de s1 para buscar a pergunta e todas as suas respostas,
            # criando uma string de contexto completa para o LLM.
            post_content = create_llm_input_string(str(row['id']))

            response = chain.invoke({"post": post_content})

            response['id'] = str(row['id'])
            results.append(response)

        except OutputParserException as e:
            print(
                f"Erro de parsing na resposta do LLM para o post ID {row['id']}: {e}")
        except Exception as e:
            print(
                f"Erro inesperado ao processar o post ID {row['local_id']}: {e}")

    output_path = MISUSE_CASES
    print(
        f"\nProcessamento concluído. {len(results)} resultados foram gerados.")
    print(f"Salvando resultados em: {output_path}")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        print("Arquivo salvo com sucesso!")
    except Exception as e:
        print(f"Erro ao salvar o arquivo JSON: {e}")


if __name__ == "__main__":
    test_on_sample()
