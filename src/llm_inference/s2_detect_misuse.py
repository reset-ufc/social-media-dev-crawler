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


def detect_misuse_post(llm, limit=0):
    """
    Função principal para processar posts, detectar usos indevidos de criptografia
    e salvar os resultados.
    """

    print(f"Iniciando detecção de uso indevido.")

    input_path = PREPROCESSED_POSTS
    if not input_path.exists():
        print(f"Erro: Arquivo de entrada não encontrado em '{input_path}'.")
        return

    print(f"Carregando posts de: {input_path}")
    df = pd.read_csv(input_path, dtype={'id': str, 'question_id': str})

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

    if limit > 0:
        questions_df = questions_df.head(limit)
        print(
            f"Aplicando limite: os próximos {limit} posts serão processados.")

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
    detect_misuse_post(
        ChatOllama(model="llama3.2:3b", temperature=0, format="json"),
        10
    )
