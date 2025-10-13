import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import PREPROCESSED_POSTS
import warnings


def create_llm_input_string(post_id: str, posts_filepath: str = PREPROCESSED_POSTS) -> str:
    """
    Lê um arquivo de posts pré-processados, encontra uma pergunta específica pelo ID,
    e formata seu conteúdo e o de suas respostas em uma única string para o LLM.

    Args:
        post_id: O ID da pergunta a ser formatada.
        posts_filepath: O caminho para o arquivo CSV com os posts.

    Returns:
        Uma string formatada contendo a pergunta e suas respostas ordenadas.
        Retorna uma string vazia se a pergunta não for encontrada ou ocorrer um erro.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", pd.errors.DtypeWarning)
            df = pd.read_csv(posts_filepath, dtype={
                             'id': str, 'question_id': str})
    except FileNotFoundError:
        print(
            f"ERRO: Arquivo de posts pré-processados não encontrado em: {posts_filepath}")
        return ""

    df['creation_date'] = pd.to_datetime(df['creation_date'], errors='coerce')

    question_series = df[(df['id'] == post_id) & (df['type'] == 'post')]
    if question_series.empty:
        return ""

    question = question_series.iloc[0]

    related_answers = df[(df['question_id'] == post_id)
                         & (df['type'] == 'answer')]
    sorted_answers = related_answers.sort_values(by='creation_date')
    post_str = f"""Id: {question['id']}
Site: {question['site']}
Title: {question['title']}

Question body:

{str(question.get('body', ''))}

End of body
"""
    for _, answer in sorted_answers.iterrows():
        post_str += f"""
Answer:

{str(answer.get('body', ''))}

End of Answer
"""
    return post_str.strip()


def main():
    """
    Função principal que demonstra como usar create_llm_input_string.
    """
    print(create_llm_input_string('853'))


if __name__ == "__main__":
    main()
