import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import Tuple
import pandas as pd
from tqdm import tqdm
import html
import re
from paths import *
from utils import get_logger

logger = get_logger(__name__)


def is_valid_code(block: str) -> bool:
    """
    Retorna True se o conteúdo parecer um código de programação real.
    Evita blocos matemáticos como 'C1⊕C2' e mantém código válido.
    """
    block = block.strip()
    if not block:
        return False

    # Muito curto e sem símbolos típicos de código
    if len(block) < 5 and not re.search(r"[;{}()\[\]=#.:]", block):
        return False

    # Rejeita fórmulas matemáticas e símbolos de texto técnico
    if re.search(r"[⊕±Σ∑√∫≈≤≥∞≠→←⇔×÷∂∇µλφπΩωβ]", block):
        return False

    # Aceita padrões típicos de código
    patterns = [
        r"\b(def|class|import|for|if|return|try|catch|new|public|void|const|var|function|while|static|int|char|String|print|AES|RSA|Key)\b",
        r"[;{}()\[\]=]",  # símbolos estruturais
        r"[#<>/]"  # possíveis trechos HTML/script
    ]
    return any(re.search(p, block) for p in patterns)


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
            r'(\S)(</code\s*>)', r'\1\n\2', modified_block,

            flags=re.DOTALL | re.IGNORECASE
        )
        code_blocks.append(modified_block)

        # Retorna um marcador temporário com quebras de linha para garantir a separação do bloco.
        return f"\n[[CODE_BLOCK_{len(code_blocks)-1}]]\n"

    # Remove todas as tags HTML restantes
    text = re.sub(r'<code>.*?</code>', _preserve_code,
                  text, flags=re.DOTALL | re.IGNORECASE)
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

    # extrai os blocos de código
    code_blocks = re.findall(r'<code>(.*?)</code>',
                             text, re.DOTALL | re.IGNORECASE)
    valid_blocks = [block.strip()
                    for block in code_blocks if is_valid_code(block)]

    # junta os válidos
    extracted_code = "\n\n".join(valid_blocks).strip()

    # limpa corpo mantendo o código formatado
    cleaned_body = clean_text(text)

    return cleaned_body, extracted_code


def main():
    logger.info(f"Carregando posts de: {FILTRED_POSTS}")
    df = pd.read_csv(FILTRED_POSTS)

    """
    Função principal para carregar, processar e salvar os dados.
    """

    logger.info(
        "Pré-processando a coluna 'body' para separar texto e código válidos")
    df['body'] = df['body'].astype(str)

    cleaned_bodies = []
    extracted_codes = []

    for body in tqdm(df['body'], desc="Limpando HTML e validando código"):
        cleaned_body, extracted_code = clean_text_and_extract_code(body)
        cleaned_bodies.append(cleaned_body)
        extracted_codes.append(extracted_code)

    df['body'] = cleaned_bodies
    df['code'] = extracted_codes

    output_path = PREPROCESSED_POSTS
    df.to_csv(output_path, index=False)

    logger.info(f" Processamento concluído. Arquivo salvo em: {output_path}")
    logger.info(
        f" {sum(bool(c) for c in extracted_codes)} posts possuem código válido extraído.")


if __name__ == "__main__":
    main()
