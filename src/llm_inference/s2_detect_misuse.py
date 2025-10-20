from s0_prompts import *
from s1_make_llm_input import post_analyze_string, get_post_metadata
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


def get_processed_ids(filepath: Path) -> set:
    """Lê um arquivo JSON e retorna um conjunto de IDs já processados."""
    if not filepath.exists():
        return set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Lê o arquivo, tratando o caso de JSON incompleto (sem ']')
            content = f.read()
            if not content.strip().endswith(']'):
                content = content.rsplit(',', 1)[0] + '\n]'
            data = json.loads(content)
        return {item['id'] for item in data if 'id' in item}
    except (json.JSONDecodeError, IndexError):
        return set()


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

    df = pd.read_csv(input_path, dtype={'id': str, 'question_id': str})
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

    processed_ids = get_processed_ids(output_path)
    if processed_ids:
        print(
            f"Retomando. {len(processed_ids)} posts já processados foram encontrados.")
        sample_df = sample_df[~sample_df['id'].astype(str).isin(processed_ids)]

    print(f"Processando {len(sample_df)} posts para o teste...")

    processed_count = 0
    # Se não há IDs processados, abre em modo de escrita para criar o arquivo.
    if not processed_ids:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('[\n')

    # Abre em modo 'r+' para ler e escrever, permitindo anexar ao JSON existente.
    with open(output_path, 'r+', encoding='utf-8') as f:
        # Se o arquivo já tinha conteúdo, move o cursor para antes do ']' final
        if processed_ids:
            f.seek(0, os.SEEK_END)  # Vai para o final
            f.seek(f.tell() - 2, os.SEEK_SET)  # Recua 2 caracteres ('\n]')
            f.truncate()

        for _, row in tqdm(sample_df.iterrows(), total=len(sample_df), desc="Analisando Posts de Teste"):
            try:
                post_id = str(row['id'])
                post_content = post_analyze_string(post_id)
                metadata_content = get_post_metadata(post_id)
                response = chain.invoke({
                    "metadata": metadata_content,
                    "post": post_content
                })

                response['id'] = post_id
                if 'meta' not in response:
                    response['meta'] = {}
                response['meta']['post_id'] = post_id
                response['site'] = str(row['site'])

                # Adiciona uma vírgula se não for o primeiro item do arquivo
                if f.tell() > 2:  # > '[\n'
                    f.write(',\n')

                json.dump(response, f, indent=4, ensure_ascii=False)
                f.flush()
                processed_count += 1

            except Exception as e:
                print(f"Erro ao processar o post de teste ID {row['id']}: {e}")

        f.write('\n]\n')

    print(
        f"\nProcessamento de teste concluído. {processed_count} resultados foram gerados.")
    print(f"Salvando resultados em: {output_path}")
    print("\n--- FIM DO MODO DE TESTE ---")


def detect_misuse_post():
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
    df = pd.read_csv(input_path, dtype={'id': str, 'question_id': str})

    llm = ChatOllama(model="llama3.2:3b", temperature=0, format="json")

    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        hier_v1()
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt_template | llm | parser

    output_path = MISUSE_CASES
    questions_df = df[df['type'] == 'question'].copy()

    processed_ids = get_processed_ids(output_path)
    if processed_ids:
        print(
            f"Retomando. {len(processed_ids)} posts já processados foram encontrados.")
        questions_df = questions_df[~questions_df['id'].astype(
            str).isin(processed_ids)]

    total = len(questions_df)
    print(
        f"Processando {total} posts com o LLM. Isso pode levar um tempo...")
    print(f"Os resultados serão salvos em tempo real em: {output_path}")

    processed_count = 0
    if not processed_ids:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('[\n')

    with open(output_path, 'r+', encoding='utf-8') as f:
        if processed_ids:
            f.seek(0, os.SEEK_END)
            f.seek(f.tell() - 2, os.SEEK_SET)
            f.truncate()

        for _, row in tqdm(questions_df.iterrows(), total=total, desc="Analisando Posts"):
            try:
                post_id = str(row['id'])
                post_content = post_analyze_string(post_id)
                metadata_content = get_post_metadata(post_id)
                response = chain.invoke({
                    "metadata": metadata_content,
                    "post": post_content
                })

                response['id'] = post_id
                if 'meta' not in response:
                    response['meta'] = {}
                response['meta']['post_id'] = post_id
                response['site'] = str(row['site'])

                if f.tell() > 2:
                    f.write(',\n')

                json.dump(response, f, indent=4, ensure_ascii=False)
                f.flush()
                processed_count += 1

            except OutputParserException as e:
                print(
                    f"Erro de parsing na resposta do LLM para o post ID {row['id']}: {e}")
            except Exception as e:
                print(
                    f"Erro inesperado ao processar o post ID {row['id']}: {e}")

        f.write('\n]\n')

    print(
        f"\nProcessamento concluído. {processed_count} resultados foram gerados e salvos.")


if __name__ == "__main__":
    detect_misuse_post()
