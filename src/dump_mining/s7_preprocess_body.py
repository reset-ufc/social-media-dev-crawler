import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_logger
from paths import *
import re
import html
from tqdm import tqdm
import pandas as pd
from typing import Tuple


logger = get_logger(__name__)


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""  # Retorna string vazia se a entrada não for string

    # Desescapa entidades HTML (&lt;, &gt;, &amp;, etc.)
    text = html.unescape(text)

    # Substitui <br>, <p>, </p> por quebras de linha
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p>', '', text, flags=re.IGNORECASE)

    # Converte "\\n" em quebras reais
    text = text.replace("\\n", "\n")

    # Preserva conteúdo dentro de <code>...</code> para não ser removido
    code_blocks = []

    def _preserve_code(match):
        original_block = match.group(0)

        # Adiciona uma quebra de linha logo após a tag de abertura `<code>`
        # Usamos re.sub com count=1 para substituir apenas a primeira ocorrência.
        modified_block = re.sub(r'(<code\b.*?>)', r'\1\n',
                                original_block, count=1, flags=re.IGNORECASE)

        # Adiciona uma quebra de linha antes da tag de fechamento `</code>`
        # Isso garante que o conteúdo não fique colado ao final da tag.
        modified_block = re.sub(
            r'(\S)(</code\s*>)', r'\1\n\2', modified_block, flags=re.DOTALL | re.IGNORECASE)

        code_blocks.append(modified_block)

        # Retorna um marcador temporário com quebras de linha para garantir a separação do bloco.
        return f"\n[[CODE_BLOCK_{len(code_blocks)-1}]]\n"

    text = re.sub(r'<code>.*?</code>', _preserve_code,
                  text, flags=re.DOTALL | re.IGNORECASE)

    # Remove todas as tags HTML restantes
    text = re.sub(r'<[^>]+>', '', text)

    # Restaura os blocos de código que foram preservados
    for i, code_block in enumerate(code_blocks):
        text = text.replace(f"[[CODE_BLOCK_{i}]]", code_block)

    # Remove espaços e múltiplas quebras de linha redundantes
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    text = text.strip()

    return text


def clean_text_and_extract_code(text: str) -> Tuple[str, str]:
    """
    Limpa o texto HTML do corpo de um post, mantendo o código nele,
    e também extrai o conteúdo das tags <code> para uma coluna separada.

    Args:
        text: O texto HTML bruto.

    Returns:
        Uma tupla contendo (texto_limpo, codigo_extraido).
    """
    if not isinstance(text, str):
        return "", ""

    # 1. Extrai todos os blocos de código para a coluna 'code'
    code_blocks = re.findall(r'<code>.*?</code>', text,
                             re.DOTALL | re.IGNORECASE)
    # Concatena todos os blocos de código encontrados sem separadores,
    # conforme solicitado (ex: <code>...</code><code>...</code>).
    extracted_code = "".join(code_blocks)

    # 2. Limpa o texto do corpo, mas preservando os blocos de código dentro dele
    # A função clean_text agora é responsável por essa preservação.
    cleaned_body = clean_text(text)

    return cleaned_body, extracted_code


def main():
    """
    Função principal para carregar, processar e salvar os dados.
    """
    logger.info(f"Carregando posts de: {FILTRED_POSTS}")
    df = pd.read_csv(FILTRED_POSTS)

    logger.info("Pré-processando a coluna 'body' para separar texto e código...")
    df['body'] = df['body'].astype(str)

    # Aplica a função e descompacta os resultados em duas novas listas
    cleaned_bodies = []
    extracted_codes = []
    for body in tqdm(df['body'], desc="Limpando HTML e extraindo código"):
        cleaned_body, extracted_code = clean_text_and_extract_code(body)
        cleaned_bodies.append(cleaned_body)
        extracted_codes.append(extracted_code)

    df['body'] = cleaned_bodies
    df['code'] = extracted_codes

    output_path = PREPROCESSED_POSTS
    df.to_csv(output_path, index=False)
    logger.info(f"Processamento concluído. Arquivo salvo em: {output_path}")


if __name__ == "__main__":
    main()
