import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import re
import pandas as pd
from paths import PREPROCESSED_POSTS, HIER_CODE_DETECTION
import json



def get_all_code_blocks(post_id: str, site_alias: str, posts_filepath: str = PREPROCESSED_POSTS) -> list[tuple[int, str]]:
    """
    Extrai todos os blocos de código de um post e os retorna como uma lista de tuplas (índice, conteúdo).

    Args:
        post_id: O ID do post a ser buscado.
        site_alias: O alias do site onde o post está.
        posts_filepath: O caminho para o arquivo CSV com os posts.

    Returns:
        Uma lista de tuplas (int, str), onde cada tupla contém o índice original
        e o conteúdo de um bloco de código. Retorna lista vazia se não houver blocos.
    """
    try:
        df = pd.read_csv(posts_filepath, dtype=str).fillna('')
    except FileNotFoundError:
        print(
            f"ERRO: Arquivo de posts pré-processados não encontrado em: {posts_filepath}")
        return []

    post_series = df[(df['id'] == post_id) & (df['site_alias'] == site_alias)]
    if post_series.empty:
        print(f"Nenhum post encontrado com ID {post_id} em {site_alias}.")
        return []

    post = post_series.iloc[0]
    code_content = post.get('code', '')

    if not code_content:
        return []

    # Regex para encontrar <ncode>...</ncode> e capturar o número 'n' e o conteúdo.
    # Retorna uma lista de tuplas (str_index, content)
    found_blocks = re.findall(r'<(\d+)code>(.*?)<\/\d+code>', code_content, re.DOTALL)
    
    # Converte o índice para int
    return [(int(index), content) for index, content in found_blocks]


def get_specific_code_blocks(all_blocks: list[tuple[int, str]], indices: list[int]) -> list[tuple[int, str]]:
    """
    Seleciona blocos de código de uma lista de tuplas com base nos índices fornecidos.

    Args:
        all_blocks: Uma lista de tuplas (índice, conteúdo) de blocos de código.
        indices: Uma lista de inteiros (1-based) para selecionar os blocos.

    Returns:
        Uma lista contendo as tuplas dos blocos de código selecionados.
    """
    # Cria um dicionário para busca rápida dos blocos pelo índice original
    blocks_by_index = {index: content for index, content in all_blocks}
    
    selected_blocks = []
    # Itera sobre os índices desejados para manter a ordem de `indices`
    for i in sorted(list(set(indices))): # Usar sorted para ter uma ordem previsível
        if i in blocks_by_index:
            selected_blocks.append((i, blocks_by_index[i]))
            
    return selected_blocks


# Create inputs


def get_post_metadata(post_id: str, site_alias: str, posts_filepath: str = PREPROCESSED_POSTS) -> str:
    """
    Busca metadados de um post (site, ID e tags) e os formata em uma string.

    Args:
        post_id: O ID do post a ser buscado.
        site: O site onde o post está.
        posts_filepath: O caminho para o arquivo CSV com os posts.

    Returns:
        Uma string formatada com site, ID e tags do post, ou vazia se não encontrado.
    """
    try:
        # dtype=str garante que todos os IDs sejam lidos como texto, evitando erros de tipo.
        df = pd.read_csv(posts_filepath, dtype=str)
    except FileNotFoundError:
        print(f"ERRO: Arquivo de posts não encontrado em: {posts_filepath}")
        return ""

    post_series = df[(df['id'] == post_id) & (df['site_alias'] == site_alias)]
    if post_series.empty:
        print(f"Nenhum post encontrado com ID {post_id}.")
        return ""

    post = post_series.iloc[0]
    site_alias = post.get('site_alias', 'N/A')
    tags = post.get('tags', '')
    return f"[SITE]: {site_alias} [POST_ID]: {post_id}\n[TAGS]: {tags}"


def post_analyze_string(post_id: str, site: str, posts_filepath: str = PREPROCESSED_POSTS) -> str:
    """
    Lê um arquivo de posts pré-processados, encontra uma pergunta específica pelo ID e site,
    e formata seu conteúdo e o de suas respostas em uma única string para o LLM.

    Args:
        post_id: O ID da pergunta a ser formatada.
        site: O site onde o post está.
        posts_filepath: O caminho para o arquivo CSV com os posts.

    Returns:
        Uma string formatada contendo a pergunta e suas respostas ordenadas.
        Retorna uma string vazia se a pergunta não for encontrada ou ocorrer um erro.
    """
    try:
        # dtype=str garante que todos os IDs sejam lidos como texto.
        df = pd.read_csv(posts_filepath, dtype=str)
    except FileNotFoundError:
        print(
            f"ERRO: Arquivo de posts pré-processados não encontrado em: {posts_filepath}")
        return ""

    df['creation_date'] = pd.to_datetime(df['creation_date'], errors='coerce')

    # Localiza a pergunta
    question_series = df[(df['id'] == post_id) & (
        df['site'] == site) & (df['type'] == 'question')]
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


def code_analyze_string(post_id: str, site_alias: str, posts_filepath: str = PREPROCESSED_POSTS) -> str:
    """
    Formata todos os blocos de código de um post em uma única string numerada,
    usando os índices originais das tags <ncode>.

    Args:
        post_id: O ID do post a ser buscado.
        site_alias: O alias do site onde o post está.
        posts_filepath: O caminho para o arquivo CSV com os posts.

    Returns:
        Uma string formatada com todos os blocos de código.
    """
    code_blocks = get_all_code_blocks(post_id, site_alias, posts_filepath)

    if not code_blocks:
        return ""

    # Usa o índice original extraído da tag
    formatted_blocks = [f"code {index}:\n{block}" for index,
                        block in code_blocks]

    return "\n".join(formatted_blocks)


def code_analyze_specific_code_blocks(post_id: str, site: str, indices: list[int], posts_filepath: str = PREPROCESSED_POSTS) -> str:
    """
    Seleciona e formata blocos de código específicos de um post, usando os índices
    originais das tags <ncode>.

    Args:
        post_id: O ID do post a ser buscado.
        site: O alias do site onde o post está.
        indices: A lista de índices (1-based) dos blocos de código a serem selecionados.
        posts_filepath: O caminho para o arquivo CSV com os posts.

    Returns:
        Uma string formatada com os blocos de código selecionados.
    """
    all_blocks = get_all_code_blocks(post_id, site, posts_filepath)

    if not all_blocks:
        return ""

    # A função get_specific_code_blocks agora retorna as tuplas (index, content)
    specific_blocks = get_specific_code_blocks(all_blocks, indices)

    # O índice já é o correto (original), então basta formatar
    formatted_blocks = [f"code {index}:\n{block}" for index, block in specific_blocks]

    return "\n".join(formatted_blocks)


# pass inputs


def input_analysis_specific_codes(case, path=HIER_CODE_DETECTION) -> dict:
    """
    For type step. Extracts specific code blocks from a post based on detected misuses.
    It reads a jsonl file containing misuse detections, finds the entry corresponding
    to the post, extracts the code indices of misuses, and formats the specified
    code blocks for analysis.
    """
    question_id = case.get('question_id')
    site = case.get('site')
    if not question_id or not site:
        return None

    code_indices = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    # NOTE: Assuming the jsonl file contains 'id' and 'site' to match with the case.
                    # The user-provided structure did not include them, but it's necessary to link
                    # detections to the correct post.
                    if str(data.get('question_id')) == str(question_id) and data.get('site') == site:
                        if data.get('has_misuse') and 'misuses' in data:
                            for misuse in data['misuses']:
                                if 'code_index' in misuse:
                                    code_indices.append(
                                        int(misuse['code_index']))
                        break  # Found the entry for the post, no need to read further.
                except (json.JSONDecodeError, AttributeError):
                    print(f'Error to decode json line:\n{data}')
    except FileNotFoundError:
        print(
            f"Warning: Detection file not found at {path}. Cannot select specific code blocks.")
        return None

    if not code_indices:
        return None  # No misuses with code blocks found for this post.

    unique_indices = sorted(list(set(code_indices)))

    code_input = code_analyze_specific_code_blocks(
        str(question_id), site, unique_indices)
    if not code_input:
        return None

    metadata_input = get_post_metadata(str(question_id), site)

    return {"codes": code_input, "post_metadata": metadata_input}


def input_analyze_all_codes(case) -> dict:
    """Processes a case for code analysis."""
    post_id = case.get('id')
    site_alias = case.get('site_alias')
    if not post_id or not site_alias:
        return None
    code_input = code_analyze_string(str(post_id), site_alias)
    if not code_input:
        return None

    metadata_input = get_post_metadata(str(post_id), site_alias)

    return {"codes": code_input, "post_metadata": metadata_input}


def input_judgement_all_codes(case):
    """Processes a case for the judging pipeline."""
    post_id = case.get('question_id')
    site = case.get('site', '')

    code_input = code_analyze_string(str(post_id), site)
    analysis_input = json.dumps(case, indent=2)

    return {"codes": code_input, "analysis": analysis_input}


def main():
    print(code_analyze_specific_code_blocks('2945', 'crypto', [1, 3]))


if __name__ == "__main__":
    main()
