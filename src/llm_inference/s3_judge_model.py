from s0_prompts import judge_v1
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

    print(
        f"Encontrados {len(previous_results)} resultados para serem julgados.")

    llm = ChatOllama(model="llama3.2:3b", temperature=0, format="json")
    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        judge_v1()
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt_template | llm | parser

    results = []

    for prev_result in tqdm(previous_results, desc="Julgando Classificações"):
        try:
            post_id = prev_result.get('id')
            if not post_id:
                continue

            metadata_content = get_post_metadata(post_id)
            post_content = post_analyze_string(post_id)

            response = chain.invoke({
                # O prompt de julgamento espera 'metadata' e 'post'
                "metadata": metadata_content,
                "post": post_content,
                "response": json.dumps(prev_result, indent=2)
            })

            response['id'] = post_id
            results.append(response)

        except OutputParserException as e:
            print(
                f"Erro de parsing na resposta do LLM para o post ID {post_id}: {e}")
        except Exception as e:
            print(f"Erro inesperado ao processar o post ID {post_id}: {e}")

    output_path = JUDGEMENT
    print(
        f"\nProcessamento concluído. {len(results)} julgamentos foram gerados.")
    print(f"Salvando resultados em: {output_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print("Arquivo de julgamentos salvo com sucesso!")


if __name__ == "__main__":
    judge_misuse_post()
