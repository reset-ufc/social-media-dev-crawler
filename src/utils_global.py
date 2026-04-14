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
    Open Posts.xml inside a .7z file in streaming mode using pipe.
    """
    # 'e' (extract), '-so' (send to stdout)
    # stream the XML content directly to Python RAM without passing through disk
    cmd = ["7z", "e", archive_path, posts_filename, "-so"]

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

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
    Receives the raw value from the tags column and returns a list of tags.
    Supports common formats:
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
    """Standardizes the date format, ignoring errors."""
    try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
        return dt.strftime('%Y/%m/%d, %H:%M:%S')
    except Exception:
        return ts


def get_logger(name: str, level=logging.INFO) -> logging.Logger:
    """
    Configures and returns a logger that writes to console and to a file.
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger  # Avoid adding duplicate handlers

    logger.setLevel(level)
    formatter = logging.Formatter(
        '%(levelname)s - %(message)s')

    # Handler for console
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Handler for file
    ensure_parent_dir(DUMP_MINING_LOG_FILE)
    fh = logging.FileHandler(DUMP_MINING_LOG_FILE, encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


def make_dir_structure():
    current_file_dir = Path(__file__).resolve().parent

    base_dir = current_file_dir.parent
    dirs = [
        base_dir / 'Extraidos dump',
        base_dir / "data" / "data_mining" / "s1",
        base_dir / "data" / "data_mining" / "s2",
        base_dir / "data" / "Lda" / "csvs",
        base_dir / "data" / "Lda" / "models",
        base_dir / "data" / "notebook_outputs" / "rq1" / 'plots',
        base_dir / "data" / "notebook_outputs" / "rq2" / 'plots',
        base_dir / "data" / "notebook_outputs" / "rq2" / 'csvs',
        base_dir / "data" / "notebook_outputs" / "rq3" / 'plots',
        base_dir / "data" / "notebook_outputs" / "rq4" / 'plots',

    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    make_dir_structure()
