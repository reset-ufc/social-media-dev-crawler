import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import subprocess
import xml.etree.ElementTree as ET
import pandas as pd
import csv
from paths import *
from utils_global import *

# Garante acesso aos módulos de diretórios superiores


logger = get_logger(__name__)

POST_FEATURES = [
    'site_alias', 'tags', 'question_id', 'accepted_answer_id', 'answer_count',
    'creation_date', 'last_activity_date', 'last_edit_date',
    'owner_id', 'score', 'view_count', 'title', 'body',
    'local_id', 'site'
]

def get_all_related_tags():
    """Lê todas as tags relacionadas do arquivo consolidado R_TAGS."""
    try:
        df = pd.read_csv(R_TAGS)
        related_tags = set(df['tag'])
        logger.info(f"Total de tags relacionadas carregadas: {len(related_tags)}")
        return related_tags
    except Exception as e:
        logger.error(f"Erro ao ler arquivo de tags relacionadas: {e}")
        return set()

def initialize_csv(path):
    """Cria o CSV com cabeçalho, se ainda não existir."""
    if not os.path.exists(path):
        ensure_parent_dir(path)
        with open(path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(POST_FEATURES)

def find_and_save_related_posts():
    """Procura e salva posts via Streaming para evitar lotar o disco."""

    related_tags = get_all_related_tags()
    if not related_tags:
        logger.error("Nenhuma tag relacionada encontrada. Abortando.")
        return

    # Usamos um set para evitar duplicatas se necessário, mas mantendo a lógica original
    processed_posts = set()
    site_post_counts = {}

    initialize_csv(RELEATED_POSTS)

    for site_alias, site_name in SITES.items():
        logger.info(f"\n--- Processando site: {site_alias} (Streaming) ---")

        site_archive = os.path.join(DUMP, f"{site_name}")
        site_count = 0

        if not os.path.exists(site_archive):
            logger.warning(f"Arquivo não encontrado: {site_archive}")
            continue

        try:
            # Comando 7z para extrair direto para o stdout (Pipe)
            # 'e' extrai, '-so' envia para o buffer de saída
            posts_xml_path = "Posts.xml"
            cmd = ["7z", "e", site_archive, posts_xml_path, "-so"]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # iterparse processa o stream do XML sem salvar o arquivo no disco
            context = ET.iterparse(process.stdout, events=("end",))
            
            batch = []
            batch_size = 500  # Otimiza a escrita no HD

            for _, elem in context:
                if elem.tag != "row":
                    continue

                # Processa apenas perguntas (PostTypeId = 1)
                if elem.attrib.get("PostTypeId") != "1":
                    elem.clear()
                    continue

                post_id = elem.attrib.get("Id")
                if post_id in processed_posts:
                    elem.clear()
                    continue

                tags_field = elem.attrib.get("Tags", "")
                if tags_field:
                    post_tags = set(extract_tag_list(tags_field))
                    
                    # Interseção eficiente entre sets
                    if not related_tags.isdisjoint(post_tags):
                        row = [
                            site_alias,
                            ";".join(post_tags),
                            post_id,
                            elem.attrib.get("AcceptedAnswerId", ""),
                            elem.attrib.get("AnswerCount", "0"),
                            safe_date(elem.attrib.get("CreationDate", "")),
                            safe_date(elem.attrib.get("LastActivityDate", "")),
                            safe_date(elem.attrib.get("LastEditDate", "")),
                            elem.attrib.get("OwnerUserId", ""),
                            elem.attrib.get("Score", "0"),
                            elem.attrib.get("ViewCount", "0"),
                            elem.attrib.get("Title", ""),
                            elem.attrib.get("Body", ""),
                            post_id,
                            site_name
                        ]
                        batch.append(row)
                        processed_posts.add(post_id)
                        site_count += 1

                # Escrita em lote para performance
                if len(batch) >= batch_size:
                    with open(RELEATED_POSTS, "a", encoding="utf-8", newline="") as f_csv:
                        csv.writer(f_csv).writerows(batch)
                    batch = []

                # Crucial: limpa o elemento da RAM
                elem.clear()

            # Escreve o restante do lote
            if batch:
                with open(RELEATED_POSTS, "a", encoding="utf-8", newline="") as f_csv:
                    csv.writer(f_csv).writerows(batch)

            process.stdout.close()
            process.wait()

        except Exception as e:
            logger.error(f"Erro ao processar {site_alias}: {e}", exc_info=True)
            continue

        site_post_counts[site_alias] = site_count
        logger.info(f"  Posts encontrados: {site_count}")

    # Log de Resumo Final
    logger.info("\n##### RESUMO FINAL #####")
    total_posts = sum(site_post_counts.values())
    for site, count in site_post_counts.items():
        logger.info(f"  - {site}: {count} posts")
    logger.info(f"  - TOTAL GERAL: {total_posts}")
    logger.info("##### FIM DO RESUMO #####\n")

def main():
    logger.info("Iniciando busca otimizada (Zero-Disk-Extra)...")
    find_and_save_related_posts()
    logger.info("Concluído!")

if __name__ == "__main__":
    main()