import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
import tempfile
import py7zr
import xml.etree.ElementTree as ET
import pandas as pd
from paths import *
from utils import *



logger = get_logger(__name__)


# --- Calcula C ---
def calculate_c():
    """
    Calcula c = número total de perguntas (PostTypeId=1)
    que contêm QUESTION_TAG nos dumps compactados (.7z).
    """
    logger.info("Calculando a constante 'c' ...")
    c = 0

    for site_alias, site_file in SITES.items():
        archive_path = os.path.join(BASE_DIR, site_file)
        if not os.path.exists(archive_path):
            logger.warning(
                f"[{site_alias}] Arquivo .7z não encontrado em: {archive_path}")
            continue

        logger.info(f"[{site_alias}] Lendo compactado: {archive_path}")
        try:
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                posts_files = [
                    f for f in archive.getnames() if "Posts.xml" in f]
                if not posts_files:
                    logger.warning(
                        f"[{site_alias}] Nenhum Posts.xml dentro do .7z.")
                    continue

                temp_dir = tempfile.mkdtemp()
                archive.extract(path=temp_dir, targets=posts_files)
                posts_path = os.path.join(temp_dir, posts_files[0])

                logger.info(f"[{site_alias}] Processando {posts_path} ...")

                context = ET.iterparse(posts_path, events=("start",))
                for _, elem in context:
                    if elem.tag == "row" and elem.attrib.get("PostTypeId") == "1":
                        tags_field = elem.attrib.get("Tags", "")
                        tags = extract_tag_list(tags_field)
                        if QUESTION_TAG in tags:
                            c += 1
                    elem.clear()
                del context  # Garante que o arquivo XML seja liberado

                shutil.rmtree(temp_dir)

        except Exception as e:
            logger.error(
                f"[{site_alias}] Erro ao processar: {e}", exc_info=True)

    logger.info(f"Constante c = {c}")
    return c


# --- Calcula H2 ---
def calculate_h2():
    """Calcula h2 = a / c e grava no arquivo de tags relacionadas."""
    logger.info("Calculando h2 ...")

    if not os.path.exists(RELEATED_TAGS):
        logger.error(f"{RELEATED_TAGS} não encontrado. Rode H1 primeiro.")
        return

    df = pd.read_csv(RELEATED_TAGS)
    if 'a' not in df.columns:
        logger.error(
            "Coluna 'a' não encontrada. Rode make_releated_tags() primeiro.")
        return

    df['a'] = pd.to_numeric(df['a'], errors='coerce').fillna(0).astype(int)

    c = calculate_c()
    if c <= 0:
        logger.error("Valor de c = 0. Não é possível calcular h2.")
        return

    df['h2'] = (df['a'] / c).fillna(0)
    df.to_csv(RELEATED_TAGS, index=False, encoding='utf-8')

    logger.info(
        f"Coluna 'h2' adicionada e arquivo atualizado: {RELEATED_TAGS}")


# --- Filtra H2 ---
def filter_by_h2_threshold():
    """Remove linhas com h2 < THRE2."""
    logger.info(f"Filtrando tags com h2 < {THRE2} ...")

    if not os.path.exists(RELEATED_TAGS):
        logger.error(f"{RELEATED_TAGS} não encontrado.")
        return

    df = pd.read_csv(RELEATED_TAGS)
    if 'h2' not in df.columns:
        logger.error(
            "Coluna 'h2' não encontrada. Rode calculate_h2() primeiro.")
        return

    original = len(df)
    df = df[df['h2'] >= THRE2].reset_index(drop=True)
    removed = original - len(df)

    df.to_csv(RELEATED_TAGS, index=False, encoding='utf-8')
    logger.info(
        f"Filtro aplicado. {removed} tags removidas. Salvo em: {RELEATED_TAGS}")


# --- MAIN ---
def main():
    calculate_h2()
    filter_by_h2_threshold()
    logger.info("Processo da Heurística 2 finalizado com sucesso!")
