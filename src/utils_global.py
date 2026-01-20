from pathlib import Path
import os
import re
import pandas as pd
from datetime import datetime

import logging
from paths import DATA_MINING_S2, DUMP_MINING_LOG_FILE, DUMP, SITES
import io
import subprocess
import xml.etree.ElementTree as ET

import pandas as pd

import numpy as np
from paths import *


from contextlib import contextmanager


@contextmanager
def stream_posts_from_7z(archive_path, posts_filename="Posts.xml"):
    """
    Abre Posts.xml dentro de um .7z em streaming usando pipe.
    """
    # 'e' (extract), '-so' (send to stdout)
    # joga o conteúdo do XML direto para a RAM do Python sem passar pelo disco
    cmd = ["7z", "e", archive_path, posts_filename, "-so"]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        context = ET.iterparse(process.stdout, events=("end",))
        yield context
    finally:
        if process.stdout:
            process.stdout.close()
        process.wait()


def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def extract_tag_list(tags_field):
    """
    Recebe o valor bruto da coluna tags e retorna lista de tags.
    Suporta formatos comuns:
      - "python;cryptography"
    """
    if pd.isna(tags_field) or tags_field == "":
        return []
    if '<' in tags_field and '>' in tags_field:
        return re.findall(r'<(.+?)>', tags_field)
    if ';' in tags_field:
        return [t.strip() for t in tags_field.split(';') if t.strip()]
    if '|' in tags_field:
        return [t.strip() for t in tags_field.split('|') if t.strip()]
    return [t.strip() for t in re.split(r'[\s,;|]+', tags_field) if t.strip()]


def safe_date(ts):
    """Padroniza o formato de data, ignorando erros."""
    try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
        return dt.strftime('%Y/%m/%d, %H:%M:%S')
    except Exception:
        return ts


def get_logger(name: str, level=logging.INFO) -> logging.Logger:
    """
    Configura e retorna um logger que escreve para o console e para um arquivo.
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger  # Evita adicionar handlers duplicados

    logger.setLevel(level)
    formatter = logging.Formatter(
        '%(levelname)s - %(message)s')

    # Handler para o console
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Handler para o arquivo
    ensure_parent_dir(DUMP_MINING_LOG_FILE)
    fh = logging.FileHandler(DUMP_MINING_LOG_FILE, encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger

def make_data():
    """Creates the data directory structure."""
    os.makedirs(RELEATED_TAGS_DIR, exist_ok=True)
    os.makedirs(DATA_MINING_S2, exist_ok=True)
    os.makedirs(LLM_CLASSIFICATION, exist_ok=True)
    os.makedirs(LLM_SUMMARIZATION, exist_ok=True)


from pathlib import Path

def make_dir_structure():
    current_file_dir = Path(__file__).resolve().parent
    
    base_dir = current_file_dir.parent
    dirs = [
        base_dir / 'Extraidos dump',
        base_dir / "data" / "data_mining" / "s1",
        base_dir / "data" / "data_mining" / "s2",
        base_dir / "data" / "Lda" / "csvs",
        base_dir / "data" / "Lda" / "plots",
        base_dir / "data" / "Lda" / "models",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    make_dir_structure()
    