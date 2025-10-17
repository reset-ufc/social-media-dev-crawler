import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from utils import get_logger
from paths import *
import re
import html
from tqdm import tqdm
from bs4 import BeautifulSoup
import pandas as pd


logger = get_logger(__name__)


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""

    # Desescapa entidades HTML (&lt;, &gt;, &amp;, etc.)
    text = html.unescape(text)

    # Substitui <br>, <p>, </p> por quebras de linha
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p\s*>', '', text, flags=re.IGNORECASE)

    # Converte "\\n" em quebras reais
    text = text.replace("\\n", "\n")

    # Preserva conteúdo dentro de <code>...</code>
    code_blocks = []

    def _preserve_code(match):
        code_blocks.append(match.group(0))  # mantém a tag <code> original
        return f"[[CODE_BLOCK_{len(code_blocks)-1}]]"  # marcador temporário

    text = re.sub(r'<code>.*?</code>', _preserve_code,
                  text, flags=re.DOTALL | re.IGNORECASE)

    # Remove todas as outras tags HTML restantes
    text = re.sub(r'<[^>]+>', '', text)

    # Restaura os blocos <code> preservados
    for i, code_block in enumerate(code_blocks):
        text = text.replace(f"[[CODE_BLOCK_{i}]]", code_block)

    # Remove espaços e múltiplas quebras de linha redundantes
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    text = text.strip()

    return text


def main():
    """
    Função principal para carregar, processar e salvar os dados.
    """
    logger.info(f"Carregando posts de: {FILTRED_POSTS}")
    df = pd.read_csv(FILTRED_POSTS)

    logger.info("Pré-processando a coluna 'body'...")
    df['body'] = df['body'].astype(str)
    df['body'] = [clean_text(
        body) for body in tqdm(df['body'], desc="Limpando HTML")]

    output_path = PREPROCESSED_POSTS
    df.to_csv(output_path, index=False)
    logger.info(f"Processamento concluído. Arquivo salvo em: {output_path}")


if __name__ == "__main__":
    main()
