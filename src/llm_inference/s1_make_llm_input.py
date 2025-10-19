import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings
from paths import PREPROCESSED_POSTS
import pandas as pd


def get_post_metadata(post_id: str, posts_filepath: str = PREPROCESSED_POSTS) -> str:
    """
    Busca metadados de um post (site, ID e tags) e os formata em uma string.

    Args:
        post_id: O ID do post a ser buscado.
        posts_filepath: O caminho para o arquivo CSV com os posts.

    Returns:
        Uma string formatada com site, ID e tags do post, ou vazia se não encontrado.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", pd.errors.DtypeWarning)
            df = pd.read_csv(posts_filepath, dtype={
                             'id': str, 'question_id': str})
    except FileNotFoundError:
        print(f"ERRO: Arquivo de posts não encontrado em: {posts_filepath}")
        return ""

    post_series = df[df['id'] == post_id]
    if post_series.empty:
        print(f"Nenhum post encontrado com ID {post_id}.")
        return ""

    post = post_series.iloc[0]
    site_alias = post.get('site_alias', 'N/A')
    tags = post.get('tags', '')
    return f"[SITE]: {site_alias} [POST_ID]: {post_id}\n[TAGS]: {tags}"


def post_analyze_string(post_id: str, posts_filepath: str = PREPROCESSED_POSTS) -> str:
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

    # Localiza a pergunta
    question_series = df[(df['id'] == post_id) & (df['type'] == 'question')]
    if question_series.empty:
        print(f"Nenhuma pergunta encontrada com ID {post_id}.")
        return ""

    question = question_series.iloc[0]

    # Respostas e comentários relacionados
    related_answers = df[(df['question_id'] == post_id)
                         & (df['type'] == 'answer')]

    # Coleta todos os IDs da discussão (pergunta + respostas)
    all_post_ids_in_thread = {post_id} | set(related_answers['id'])

    # Coleta todos os comentários relacionados à discussão de uma só vez
    all_comments = df[(df['question_id'].isin(
        all_post_ids_in_thread)) & (df['type'] == 'comment')]

    post_str = f"""<<<POST_DISCUSSION>>>

[TITLE]:
{question.get('title', '')}

[BODY]:
{str(question.get('body', ''))}
"""

    post_str += "\n[ANSWERS]\n"

    # Ordena respostas por data
    sorted_answers = related_answers.sort_values(
        by='creation_date', ascending=True)

    for idx, answer in enumerate(sorted_answers.itertuples(), 1):
        post_str += f"\n[ANSWER #{idx} ID: {answer.id}]:\n{answer.body.strip()}\n"

    # Adiciona todos os comentários no final
    post_str += "\n[ALL_COMMENTS]\n"
    if not all_comments.empty:
        for comment in all_comments.itertuples():
            post_str += f"Comment on Post ID {comment.question_id}: {comment.body.strip()}\n"
    else:
        post_str += "(No comments in this discussion)\n"

    post_str += "\n<<<END_POST_DISCUSSION>>>\n"
    return post_str.strip()


def code_analyze_string():
    ...


def main():
    """
    Função principal que demonstra como usar create_llm_input_string.
    """
    print(get_post_metadata("12795"))
    print(post_analyze_string("12795"))


if __name__ == "__main__":
    main()
