from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
import pandas as pd
import json
from tqdm import tqdm
from paths import *
from s1_make_llm_input import post_analyze_string, get_post_metadata
from s0_prompts import judge_v1
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


def judge_misuse_post():
    """
    Função principal para usar um LLM como 'juiz' para avaliar a qualidade
    das classificações de uso indevido geradas pelo script anterior (s2).
    """
    print("Iniciando o processo de julgamento das classificações do modelo...")

    if not MISUSE_CASES.exists():
        print(
            f"Erro: Arquivo de casos de uso indevido não encontrado em '{MISUSE_CASES}'.")
        print("Execute o script s2_detect_misuse.py primeiro.")
        return

    print(f"Carregando classificações de: {MISUSE_CASES}")
    with open(MISUSE_CASES, 'r', encoding='utf-8') as f:
        previous_results = json.load(f)

    if not previous_results:
        print("Nenhum resultado anterior encontrado para julgar.")
        return

    output_path = JUDGEMENT
    processed_ids = get_processed_ids(output_path)
    if processed_ids:
        print(
            f"Retomando. {len(processed_ids)} julgamentos já processados foram encontrados.")
        previous_results = [res for res in previous_results if res.get(
            'id') not in processed_ids]

    print(
        f"Encontrados {len(previous_results)} resultados para serem julgados.")

    llm = ChatOllama(model="llama3.2:3b", temperature=0, format="json")
    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        judge_v1()
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt_template | llm | parser

    processed_count = 0
    print(f"Os julgamentos serão salvos em tempo real em: {output_path}")

    if not processed_ids:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('[\n')

    with open(output_path, 'r+', encoding='utf-8') as f:
        if processed_ids:
            f.seek(0, os.SEEK_END)
            f.seek(f.tell() - 2, os.SEEK_SET)
            f.truncate()

        for prev_result in tqdm(previous_results, desc="Julgando Classificações"):
            try:
                post_id = prev_result.get('id')
                if not post_id:
                    continue

                metadata_content = get_post_metadata(post_id)
                post_content = post_analyze_string(post_id)

                response = chain.invoke({
                    "metadata": metadata_content,
                    "post": post_content,
                    "response": json.dumps(prev_result, indent=2)
                })

                response['id'] = post_id
                if f.tell() > 2:
                    f.write(',\n')
                json.dump(response, f, indent=4, ensure_ascii=False)
                f.flush()
                processed_count += 1

            except Exception as e:
                print(f"Erro inesperado ao processar o post ID {post_id}: {e}")

        f.write('\n]\n')

    print(
        f"\nProcessamento concluído. {processed_count} julgamentos foram gerados e salvos.")


if __name__ == "__main__":
    judge_misuse_post()
