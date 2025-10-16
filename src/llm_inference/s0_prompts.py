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



def anderson_v1() -> str:
    return _load_prompt_from_file("base.txt")


def anderson_hier_v1() -> str:
    return _load_prompt_from_file("hierarquical_v1.txt")


def judge_v1() -> str:
    return _load_prompt_from_file("judge_v1.txt")


print(anderson_hier_v1())