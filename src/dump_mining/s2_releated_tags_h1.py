import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import *
from utils import *
from collections import Counter
import shutil
import tempfile
import py7zr
import xml.etree.ElementTree as ET
import pandas as pd



logger = get_logger(__name__)


def make_releated_tags():
    """
    Cria o CSV inicial com as tags relacionadas e a coluna 'a'.
    """
    logger.info("-> make_releated_tags: começando...")
    if not os.path.exists(COARSE_QUESTIONS):
        logger.error(f"Arquivo {COARSE_QUESTIONS} não encontrado.")
        return

    df = pd.read_csv(COARSE_QUESTIONS, dtype=str)
    logger.info(f"  Linhas totais: {len(df)}")

    if 'tags' not in df.columns:
        logger.error("Coluna 'tags' não encontrada.")
        return

    df['tags'] = df['tags'].fillna('')
    df['tag_list'] = df['tags'].apply(extract_tag_list)

    num_with_question_tag = df['tag_list'].apply(
        lambda L: QUESTION_TAG in L).sum()
    logger.info(f"  Posts com '{QUESTION_TAG}': {num_with_question_tag}")

    df_filtered = df[df['tag_list'].apply(lambda L: QUESTION_TAG in L)]
    all_tags = df_filtered['tag_list'].explode().dropna()
    tag_counts = all_tags.value_counts()

    releated_tags_df = tag_counts.reset_index()
    releated_tags_df.columns = ['tag', 'a']

    if QUESTION_TAG in releated_tags_df['tag'].values:
        releated_tags_df = releated_tags_df[releated_tags_df['tag']
                                            != QUESTION_TAG]

    ensure_parent_dir(RELEATED_TAGS)
    releated_tags_df.to_csv(RELEATED_TAGS, index=False, encoding='utf-8')
    logger.info(
        f"  Arquivo salvo em: {RELEATED_TAGS} (linhas: {len(releated_tags_df)})")

# --- calculate_b atualizado para ler de .7z ------------------------


def calculate_b():
    """
    Conta 'b' diretamente dos arquivos .7z (Posts.xml dentro do dump compactado).
    """
    logger.info("-> calculate_b (com .7z): começando...")
    if not os.path.exists(RELEATED_TAGS):
        logger.error("Arquivo de tags relacionadas não encontrado.")
        return

    releated_tags_df = pd.read_csv(RELEATED_TAGS, dtype={'tag': str})
    tags_to_count = set(releated_tags_df['tag'].dropna().astype(str))
    tag_counter = Counter()

    for site_alias, site_file in SITES.items():
        archive_path = os.path.join(BASE_DIR, site_file)
        if not os.path.exists(archive_path):
            logger.warning(
                f".7z não encontrado para {site_alias}: {archive_path}")
            continue

        logger.info(f"  Lendo dump compactado: {archive_path}")
        try:
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                posts_files = [
                    f for f in archive.getnames() if "Posts.xml" in f]
                if not posts_files:
                    logger.warning(
                        f"  Nenhum Posts.xml dentro de {archive_path}")
                    continue

                temp_dir = tempfile.mkdtemp()
                archive.extract(path=temp_dir, targets=posts_files)
                posts_path = os.path.join(temp_dir, posts_files[0])

                context = ET.iterparse(posts_path, events=("start",))
                for _, elem in context:
                    if elem.tag == "row":
                        tags_field = elem.attrib.get("Tags", "")
                        if tags_field:
                            for t in extract_tag_list(tags_field):
                                if t in tags_to_count:
                                    tag_counter.update([t])
                    elem.clear()
                del context  # Garante que o arquivo XML seja liberado

                shutil.rmtree(temp_dir)

        except Exception as e:
            logger.error(
                f"Erro ao processar {archive_path}: {e}", exc_info=True)

    releated_tags_df['b'] = releated_tags_df['tag'].map(
        tag_counter).fillna(0).astype(int)
    releated_tags_df.to_csv(RELEATED_TAGS, index=False, encoding='utf-8')
    logger.info(f"  Coluna 'b' adicionada e arquivo salvo em: {RELEATED_TAGS}")

# --- Restante igual -----------------------------------------------


def calculate_h1():
    logger.info("-> calculate_h1: começando...")
    if not os.path.exists(RELEATED_TAGS):
        logger.error(f"{RELEATED_TAGS} não encontrado.")
        return
    df = pd.read_csv(RELEATED_TAGS, dtype={'a': float, 'b': float})
    if 'a' not in df.columns or 'b' not in df.columns:
        logger.error("Colunas 'a' e 'b' não existem.")
        return
    df['h1'] = (df['a'] / df['b']
                ).replace([float('inf'), -float('inf')], 0).fillna(0)
    df.to_csv(RELEATED_TAGS, index=False, encoding='utf-8')
    logger.info(f"  Coluna 'h1' calculada e salva em {RELEATED_TAGS}.")


def filter_by_h1_threshold():
    logger.info("-> filter_by_h1_threshold: começando...")
    if not os.path.exists(RELEATED_TAGS):
        logger.error(f"{RELEATED_TAGS} não encontrado.")
        return
    df = pd.read_csv(RELEATED_TAGS)
    if 'h1' not in df.columns:
        logger.error("Coluna 'h1' não encontrada.")
        return
    original = len(df)
    df = df[df['h1'] >= THRE1]
    df.to_csv(RELEATED_TAGS, index=False, encoding='utf-8')
    logger.info(
        f"  Filtragem por THRE1={THRE1} aplicada. Removidas {original - len(df)} linhas.")


def main():
    ensure_parent_dir(COARSE_QUESTIONS)
    make_releated_tags()
    calculate_b()
    calculate_h1()
    filter_by_h1_threshold()
    logger.info("Processo finalizado.")
