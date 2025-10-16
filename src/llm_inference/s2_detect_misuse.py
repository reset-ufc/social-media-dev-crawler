from s0_prompts import *
from s1_make_llm_input import create_llm_input_string
from paths import *
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


def test_on_sample(prompt_str: str, output_filename: str):
    """
    Executa o processo de detecção nos 10 primeiros posts do dataset
    usando um prompt e um arquivo de saída específicos.

    Args:
        prompt_str: A string do template do prompt a ser usado.
        output_filename: O nome do arquivo para salvar os resultados (ex: 'test_results.json').
    """
    print(
        f"--- MODO DE TESTE: Executando nos 10 primeiros posts com o arquivo de saída '{output_filename}' ---")

    input_path = PREPROCESSED_POSTS
    if not input_path.exists():
        print(f"Erro: Arquivo de entrada não encontrado em '{input_path}'.")
        return

    output_path = LLM_INFERENCE / output_filename

    df = pd.read_csv(input_path)
    if df.empty:
        print("Arquivo de entrada está vazio.")
        return

    sample_df = df.head(10)

    llm = ChatOllama(model="llama3.2:3b", temperature=0, format="json")
    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        prompt_str
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt_template | llm | parser

    results = []
    print(f"Processando {len(sample_df)} posts para o teste...")

    for _, row in tqdm(sample_df.iterrows(), total=sample_df.shape[0], desc="Analisando Posts de Teste"):
        try:
            post_content = create_llm_input_string(str(row['id']))
            response = chain.invoke({"post": post_content})

            # Garante que o ID e o site do post estejam presentes e consistentes.
            # O ID do DataFrame é a fonte da verdade.
            post_id = str(row['id'])
            # Para compatibilidade com scripts subsequentes
            response['id'] = post_id
            if 'meta' not in response:
                response['meta'] = {}
            # Para alinhar com o formato do prompt
            response['meta']['post_id'] = post_id
            # Adiciona o site para contexto
            response['site'] = str(row['site'])
            results.append(response)
        except Exception as e:
            print(f"Erro ao processar o post de teste ID {row['id']}: {e}")

    print(
        f"\nProcessamento de teste concluído. {len(results)} resultados foram gerados.")
    print(f"Salvando resultados em: {output_path}")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        print("Arquivo salvo com sucesso!")
    except Exception as e:
        print(f"Erro ao salvar o arquivo JSON: {e}")
    print("\n--- FIM DO MODO DE TESTE ---")


def main():
    """
    Função principal para processar posts, detectar usos indevidos de criptografia
    e salvar os resultados.
    """
    print("Iniciando o processo de detecção de uso indevido de criptografia...")

    input_path = PREPROCESSED_POSTS
    if not input_path.exists():
        print(f"Erro: Arquivo de entrada não encontrado em '{input_path}'.")
        return

    print(f"Carregando posts de: {input_path}")
    df = pd.read_csv(input_path)

    llm = ChatOllama(model="llama3.2:3b", temperature=0, format="json")

    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        base()
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

            # Garante que o ID e o site do post estejam presentes e consistentes.
            # O ID do DataFrame é a fonte da verdade.
            post_id = str(row['id'])
            # Para compatibilidade com scripts subsequentes
            response['id'] = post_id
            if 'meta' not in response:
                response['meta'] = {}
            # Para alinhar com o formato do prompt
            response['meta']['post_id'] = post_id
            # Adiciona o site para contexto
            response['site'] = str(row['site'])
            results.append(response)

        except OutputParserException as e:
            print(
                f"Erro de parsing na resposta do LLM para o post ID {row['id']}: {e}")
        except Exception as e:
            print(
                f"Erro inesperado ao processar o post ID {row['id']}: {e}")

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
    test_on_sample(
        prompt_str=base(),
        output_filename="base_results.json"
    )
    test_on_sample(
        prompt_str=hier_v1(),
        output_filename="hier_v1_results.json"
    )
