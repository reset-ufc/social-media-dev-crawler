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
            df = pd.read_csv(posts_filepath, dtype={'id': str, 'question_id': str})
    except FileNotFoundError:
        print(f"ERRO: Arquivo de posts pré-processados não encontrado em: {posts_filepath}")
        return ""

    df['creation_date'] = pd.to_datetime(df['creation_date'], errors='coerce')

    # Localiza a pergunta
    question_series = df[(df['id'] == post_id) & (df['type'] == 'question')]
    if question_series.empty:
        print(f"Nenhuma pergunta encontrada com ID {post_id}.")
        return ""

    question = question_series.iloc[0]

    # Respostas e comentários relacionados
    related_answers = df[(df['question_id'] == post_id) & (df['type'] == 'answer')]
    related_comments = df[(df['type'] == 'comment')]

    post_str = f"""<<<STACK_OVERFLOW_DISCUSSION>>>

[THREAD_ID]: {question['id']}

[TITLE]:
{question.get('title', '')}

[BODY]:
{str(question.get('body', ''))}

[TAGS]:
{question.get('tags', '')}

[COMMENTS on QUESTION]:
"""

    # Comentários diretos na pergunta
    question_comments = related_comments[related_comments["question_id"] == post_id]
    if not question_comments.empty:
        for i, comment in enumerate(question_comments.itertuples(), 1):
            post_str += f"Comment#{i}: {comment.body.strip()}\n"
    else:
        post_str += "(No comments)\n"

    post_str += "\n[ANSWERS]\n"

    # Ordena respostas por data
    sorted_answers = related_answers.sort_values(by='creation_date', ascending=True)

    for idx, answer in enumerate(sorted_answers.itertuples(), 1):
        post_str += f"\n[ANSWER #{idx}]:\n{answer.body.strip()}\n"

        # Comentários associados a esta resposta
        answer_comments = related_comments[related_comments["question_id"] == answer.id]
        post_str += f"\n[COMMENTS on ANSWER #{idx}]:\n"
        if not answer_comments.empty:
            for j, comment in enumerate(answer_comments.itertuples(), 1):
                post_str += f"Comment#{j}: {comment.body.strip()}\n"
        else:
            post_str += "(No comments)\n"

    post_str += "\n<<<END_DISCUSSION>>>\n"
    return post_str.strip()


def main():
    """
    Função principal que demonstra como usar create_llm_input_string.
    """
    print(create_llm_input_string("853"))


if __name__ == "__main__":
    main()
