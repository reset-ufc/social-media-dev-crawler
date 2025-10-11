from s1_make_llm_input import create_llm_input_string
from s0_prompts import detect_misuse
from paths import *
from tqdm import tqdm
import json
import pandas as pd
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_on_sample(sample_size: int = 1):
    """
    Executa o processo de detecção em uma amostra aleatória do dataset
    e imprime o resultado para verificação.

    Args:
        sample_size: O número de posts para testar.
    """
    print("--- MODO DE TESTE: Executando em uma amostra do dataset ---")

    input_path = PREPROCESSED_POSTS
    if not os.path.exists(input_path):
        print(f"Erro: Arquivo de entrada não encontrado em '{input_path}'.")
        return

    df = pd.read_csv(input_path)
    if df.empty:
        print("Arquivo de entrada está vazio.")
        return

    # Pega uma amostra aleatória
    sample_df = df.sample(n=min(sample_size, len(df)))
    row = sample_df.iloc[0]

    # Configura a cadeia LLM (mesma configuração da função main)
    llm = ChatOllama(model="gemma3:1b", temperature=0, format="json")
    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        detect_misuse()
    ).partial(format_instructions=parser.get_format_instructions())
    chain = prompt_template | llm | parser

    print(
        f"\nAnalisando post de amostra com id: {row['id']}")

    # Gera o conteúdo para o prompt
    post_content = create_llm_input_string(str(row['id']))
    print("\n--- Conteúdo enviado para o LLM ---")
    print(post_content)

    # Invoca o modelo e imprime a resposta
    response = chain.invoke({"post": post_content})
    print("\n--- Resposta recebida do LLM ---")
    print(json.dumps(response, indent=2, ensure_ascii=False))
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

    # O parser de JSON já está configurado para tratar a saída do modelo.
    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        detect_misuse()
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt_template | llm | parser

    # 3. Processamento dos Posts
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

    # 4. Salvando os resultados
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
