import os
import pandas as pd
import json
from tqdm import tqdm
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from dotenv import load_dotenv

import paths
from src import prompts


def load_api_key():
    """Carrega a chave da API da OpenAI a partir de variáveis de ambiente."""
    # Carrega variáveis de um arquivo .env no diretório do projeto
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "A chave da API da OpenAI não foi encontrada. "
            "Defina a variável de ambiente OPENAI_API_KEY ou crie um arquivo .env no diretório raiz do projeto."
        )
    return api_key


def format_post_for_prompt(row: pd.Series) -> str:
    """
    Formata uma linha do DataFrame em uma string para o prompt do LLM.
    Inclui título, corpo limpo e o corpo da resposta aceita, se houver.
    """
    post_text = f"Title: {row.get('Title', 'N/A')}\n\n"
    post_text += f"Body:\n{row.get('Cleaned_Body', '')}\n\n"

    # Adiciona a resposta aceita, se existir no mesmo post (linha)
    # Nota: A estrutura de dados atual não une perguntas e respostas em uma única linha.
    # Esta é uma implementação de exemplo se os dados fossem agregados.
    # Por enquanto, focaremos no título e corpo da pergunta.
    # if pd.notna(row.get('Answer_Body')):
    #     post_text += f"Accepted Answer:\n{row.get('Answer_Body')}"

    return post_text


def main():
    """
    Função principal para processar posts, detectar usos indevidos de criptografia
    e salvar os resultados.
    """
    print("Iniciando o processo de detecção de uso indevido de criptografia...")

    # 1. Configuração
    try:
        load_api_key()
    except ValueError as e:
        print(f"Erro: {e}")
        return

    # Carrega o arquivo de posts. Usamos o arquivo limpo do passo 6.
    # O usuário mencionou 'filtered_posts.csv', mas o script 6 gera 'releated_posts_cleaned.csv'.
    # Usaremos o que está no config.py como FILTERED_POSTS.
    input_path = paths.FILTERED_POSTS
    if not os.path.exists(input_path):
        print(f"Erro: Arquivo de entrada não encontrado em '{input_path}'.")
        print("Certifique-se de que o script 6_preprocess_body.py foi executado.")
        return

    print(f"Carregando posts de: {input_path}")
    df = pd.read_csv(input_path)

    # 2. Configuração do LangChain
    # Define o modelo, o parser de saída JSON e o template do prompt
    llm = ChatOpenAI(model="gpt-3.5-turbo-1106", temperature=0)
    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        prompts.detect_misuse()
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt_template | llm | parser

    # 3. Processamento dos Posts
    results = []
    print(
        f"Processando {len(df)} posts com o LLM. Isso pode levar um tempo...")

    for _, row in tqdm(df.iterrows(), total=df.shape[0], desc="Analisando Posts"):
        try:
            post_content = format_post_for_prompt(row)
            response = chain.invoke({"post": post_content})

            # Garante que o ID do post original seja mantido no resultado
            response['id'] = str(row['local_id'])
            results.append(response)

        except OutputParserException as e:
            print(
                f"Erro de parsing na resposta do LLM para o post ID {row['local_id']}: {e}")
        except Exception as e:
            print(
                f"Erro inesperado ao processar o post ID {row['local_id']}: {e}")

    # 4. Salvando os resultados
    output_path = paths.MISUSE_CASES
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
    main()
