from functools import lru_cache
from paths import PROMPTS_DIR
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@lru_cache(maxsize=None)
def load_prompt(filename: str, type) -> str:
    """
    Carrega o conteúdo de um prompt de um arquivo de texto.

    Args:
        filename: O nome do arquivo na pasta de prompts (ex: 'anderson_v1.txt').

    Returns:
        O conteúdo do arquivo como uma string.
    """
    try:
        if type == "h":
            from paths import HIERARCHICAL_PROMPTS_DIR
            file_path = HIERARCHICAL_PROMPTS_DIR / filename
        elif type == "f":
            from paths import FLAT_PROMPTS_DIR
            file_path = FLAT_PROMPTS_DIR / filename
        else:
            file_path = PROMPTS_DIR / filename
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(
            f"Erro: O arquivo de prompt '{filename}' não foi encontrado em '{PROMPTS_DIR}'.")
        raise


def combine_hieraruchical_codes(detection, code_type, output_file):
    ...
