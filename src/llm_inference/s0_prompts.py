from functools import lru_cache

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import PROMPTS_DIR


@lru_cache(maxsize=None)
def _load_prompt_from_file(filename: str) -> str:
    """
    Carrega o conteúdo de um prompt de um arquivo de texto.

    Args:
        filename: O nome do arquivo na pasta de prompts (ex: 'anderson_v1.txt').

    Returns:
        O conteúdo do arquivo como uma string.
    """
    try:
        file_path = PROMPTS_DIR / filename
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(
            f"Erro: O arquivo de prompt '{filename}' não foi encontrado em '{PROMPTS_DIR}'.")
        raise


def judge_code_analysis() -> str:
    return _load_prompt_from_file("judge_code_v1.txt")


def hierarquical_code_anylisis() -> str:
    return _load_prompt_from_file("hierarquical_in_code_v1.txt")