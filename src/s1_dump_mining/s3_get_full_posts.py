from utils_global import (
    safe_date,
    get_logger,
    extract_tag_list,
    ensure_parent_dir,
    stream_posts_from_7z
)
from paths import DUMP, R_TAGS, CONNECTED_POSTS, SITES
from collections import defaultdict
import pandas as pd
import csv
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


logger = get_logger(__name__)

POST_FEATURES = [
    "site_alias", "tags", "question_id", "accepted_answer_id", "answer_count",
    "creation_date", "last_activity_date", "last_edit_date",
    "owner_id", "score", "view_count", "comment_count",
    "title", "body", "site", "id", "type", "favorite_count"
]


def get_all_related_tags():
    """Lê todas as tags relacionadas do arquivo consolidado R_TAGS."""
    try:
        df = pd.read_csv(R_TAGS)
        related_tags = set(df['tag'])
        logger.info(
            f"Total de tags relacionadas carregadas: {len(related_tags)}")
        return related_tags
    except Exception as e:
        logger.error(f"Erro ao ler arquivo de tags relacionadas: {e}")
        return set()


def initialize_csv():
    """Cria o CSV de saída com cabeçalho."""
    ensure_parent_dir(CONNECTED_POSTS)
    with open(CONNECTED_POSTS, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(POST_FEATURES)


def append_batch_to_csv(batch):
    """Escreve um lote de registros no CSV."""
    if not batch:
        return
    with open(CONNECTED_POSTS, "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(batch)


def process_site_unified(site_alias, site_name, related_tags):
    """
    Processa um site em TRÊS passagens otimizadas:
    1. Identifica perguntas relevantes (PostTypeId=1)
    2. Coleta respostas dessas perguntas (PostTypeId=2)
    3. Coleta comentários de perguntas e respostas

    Retorna estatísticas do processamento.

    IMPORTANTE: question_id agora usa formato "site_alias:id" para evitar conflitos entre sites.
    """
    archive_path = os.path.join(DUMP, site_name)

    if not os.path.exists(archive_path):
        logger.warning(f"Arquivo não encontrado: {archive_path}")
        return None

    logger.info(f"\n{'='*60}")
    logger.info(f"Processando: {site_alias}")
    logger.info(f"{'='*60}")

    # Estruturas de dados para armazenar informações
    # question_id_with_site (site:id) -> atributos da pergunta
    relevant_questions = {}
    answers_data = []  # lista de atributos de respostas
    answer_id_to_question_id = {}  # mapeia answer_id original -> question_id_with_site
    posts_to_track = set()  # IDs originais de perguntas e respostas para rastrear comentários
    # post_id original -> contagem de comentários
    comment_counter = defaultdict(int)
    comments_data = []  # lista de atributos de comentários
    # mapeia ID original -> question_id_with_site (site:id)
    id_to_question_with_site = {}

    # PASSAGEM 1: Identificar perguntas relevantes
    logger.info("Fase 1/3: Identificando perguntas relevantes...")
    try:
        with stream_posts_from_7z(archive_path, "Posts.xml") as context:
            for _, elem in context:
                if elem.tag != "row":
                    continue

                # Apenas perguntas
                if elem.attrib.get("PostTypeId") != "1":
                    elem.clear()
                    continue

                # Verifica se tem tags relacionadas
                tags_field = elem.attrib.get("Tags", "")
                if not tags_field:
                    elem.clear()
                    continue

                post_tags = set(extract_tag_list(tags_field))

                # Se tem interseção com tags relacionadas
                if not related_tags.isdisjoint(post_tags):
                    question_id_original = elem.attrib.get("Id")
                    question_id_with_site = f"{site_alias}:{question_id_original}"

                    # Armazena mapeamento do ID original para o ID com site
                    id_to_question_with_site[question_id_original] = question_id_with_site

                    # Formata accepted_answer_id também com prefixo do site, se existir
                    accepted_answer_id_original = elem.attrib.get(
                        "AcceptedAnswerId", "")
                    accepted_answer_id = f"{site_alias}:{accepted_answer_id_original}" if accepted_answer_id_original else ""

                    relevant_questions[question_id_with_site] = {
                        'tags': ";".join(post_tags),
                        'question_id': question_id_with_site,
                        'accepted_answer_id': accepted_answer_id,
                        'answer_count': elem.attrib.get("AnswerCount", "0"),
                        'creation_date': safe_date(elem.attrib.get("CreationDate", "")),
                        'last_activity_date': safe_date(elem.attrib.get("LastActivityDate", "")),
                        'last_edit_date': safe_date(elem.attrib.get("LastEditDate", "")),
                        'owner_id': elem.attrib.get("OwnerUserId", ""),
                        'score': elem.attrib.get("Score", "0"),
                        'view_count': elem.attrib.get("ViewCount", "0"),
                        'favorite_count': elem.attrib.get("FavoriteCount", "0"),
                        'title': elem.attrib.get("Title", ""),
                        'body': elem.attrib.get("Body", ""),
                        'id_original': question_id_original,
                    }
                    posts_to_track.add(question_id_original)

                elem.clear()

        logger.info(
            f"  → Encontradas {len(relevant_questions)} perguntas relevantes")

    except Exception as e:
        logger.error(f"Erro na Fase 1 ({site_alias}): {e}", exc_info=True)
        return None

    # Se não encontrou perguntas, não precisa continuar
    if not relevant_questions:
        logger.info(f"  → Nenhuma pergunta relevante encontrada. Pulando site.")
        return {
            'questions': 0,
            'answers': 0,
            'comments': 0
        }

    # PASSAGEM 2: Coletar respostas das perguntas relevantes
    logger.info("Fase 2/3: Coletando respostas...")
    try:
        with stream_posts_from_7z(archive_path, "Posts.xml") as context:
            for _, elem in context:
                if elem.tag != "row":
                    continue

                # Apenas respostas
                if elem.attrib.get("PostTypeId") != "2":
                    elem.clear()
                    continue

                parent_id_original = elem.attrib.get("ParentId")

                # Se a resposta é de uma pergunta relevante
                if parent_id_original in id_to_question_with_site:
                    answer_id_original = elem.attrib.get("Id")
                    answer_id_with_site = f"{site_alias}:{answer_id_original}"
                    question_id_with_site = id_to_question_with_site[parent_id_original]

                    answers_data.append({
                        'answer_id': answer_id_with_site,
                        'answer_id_original': answer_id_original,
                        'parent_id': question_id_with_site,
                        'creation_date': safe_date(elem.attrib.get("CreationDate", "")),
                        'last_activity_date': safe_date(elem.attrib.get("LastActivityDate", "")),
                        'last_edit_date': safe_date(elem.attrib.get("LastEditDate", "")),
                        'owner_id': elem.attrib.get("OwnerUserId", ""),
                        'score': elem.attrib.get("Score", "0"),
                        'body': elem.attrib.get("Body", ""),
                    })

                    # Mapeia resposta original -> pergunta com site e adiciona ao rastreamento
                    answer_id_to_question_id[answer_id_original] = question_id_with_site
                    posts_to_track.add(answer_id_original)

                elem.clear()

        logger.info(f"  → Encontradas {len(answers_data)} respostas")

    except Exception as e:
        logger.error(f"Erro na Fase 2 ({site_alias}): {e}", exc_info=True)
        return None

    # PASSAGEM 3: Coletar comentários de perguntas e respostas
    logger.info("Fase 3/3: Coletando comentários...")
    try:
        with stream_posts_from_7z(archive_path, "Comments.xml") as context:
            for _, elem in context:
                if elem.tag != "row":
                    continue

                post_id_original = elem.attrib.get("PostId")

                # Se é comentário de pergunta ou resposta relevante
                if post_id_original in posts_to_track:
                    comment_id_original = elem.attrib.get("Id")
                    comment_id_with_site = f"{site_alias}:{comment_id_original}"

                    comments_data.append({
                        'comment_id': comment_id_with_site,
                        'post_id_original': post_id_original,
                        'creation_date': safe_date(elem.attrib.get("CreationDate", "")),
                        'user_id': elem.attrib.get("UserId", ""),
                        'score': elem.attrib.get("Score", "0"),
                        'text': elem.attrib.get("Text", ""),
                    })

                    comment_counter[post_id_original] += 1

                elem.clear()

        logger.info(f"  → Encontrados {len(comments_data)} comentários")

    except Exception as e:
        logger.error(f"Erro na Fase 3 ({site_alias}): {e}", exc_info=True)
        return None

    logger.info("Montando batch final...")
    final_batch = []

    # 1. Adicionar todas as perguntas
    for qid_with_site, q in relevant_questions.items():
        final_batch.append([
            site_alias,
            q['tags'],
            qid_with_site,  # question_id com formato site:id
            q['accepted_answer_id'],  # já está com formato site:id se existir
            q['answer_count'],
            q['creation_date'],
            q['last_activity_date'],
            q['last_edit_date'],
            q['owner_id'],
            q['score'],
            q['view_count'],
            # contagem de comentários usando ID original
            comment_counter.get(q['id_original'], 0),
            q['title'],
            q['body'],
            site_name,
            qid_with_site,  # id com formato site:id
            "question",
            q['favorite_count']  # FavoriteCount apenas para perguntas
        ])

    # 2. Adicionar todas as respostas
    for a in answers_data:
        final_batch.append([
            site_alias,
            "",  # respostas não têm tags
            a['parent_id'],  # question_id com formato site:id
            "",  # accepted_answer_id (não aplicável)
            "",  # answer_count (não aplicável)
            a['creation_date'],
            a['last_activity_date'],
            a['last_edit_date'],
            a['owner_id'],
            a['score'],
            "",  # view_count (não aplicável)
            # usando ID original para contar
            comment_counter.get(a['answer_id_original'], 0),
            "",  # title (não aplicável)
            a['body'],
            site_name,
            a['answer_id'],  # id com formato site:id
            "answer",
            ""  # favorite_count (não aplicável para respostas)
        ])

    # 3. Adicionar todos os comentários
    for c in comments_data:
        post_id_original = c['post_id_original']

        # Determina a qual pergunta o comentário pertence
        question_id = (id_to_question_with_site.get(post_id_original) or
                       answer_id_to_question_id.get(post_id_original))

        if question_id:
            final_batch.append([
                site_alias,
                "",  # comentários não têm tags
                question_id,  # question_id com formato site:id
                "",  # campos não aplicáveis
                "",
                c['creation_date'],
                "",  # last_activity_date (não aplicável)
                "",  # last_edit_date (não aplicável)
                c['user_id'],
                c['score'],
                "",  # view_count (não aplicável)
                "",  # comment_count (não aplicável)
                "",  # title (não aplicável)
                c['text'],
                site_name,
                c['comment_id'],  # id com formato site:id
                "comment",
                ""  # favorite_count (não aplicável para comentários)
            ])

    append_batch_to_csv(final_batch)
    logger.info(f"✓ Batch gravado com sucesso!")

    return {
        'questions': len(relevant_questions),
        'answers': len(answers_data),
        'comments': len(comments_data)
    }


def main():
    """Função principal que coordena todo o processo."""
    logger.info("="*60)
    logger.info("EXTRAÇÃO UNIFICADA DE POSTS E ELEMENTOS RELACIONADOS")
    logger.info("="*60)

    # Carregar tags relacionadas
    related_tags = get_all_related_tags()
    if not related_tags:
        logger.error("Nenhuma tag relacionada encontrada. Abortando.")
        return

    initialize_csv()

    site_stats = {}

    for site_alias, site_name in SITES.items():
        stats = process_site_unified(site_alias, site_name, related_tags)

        if stats:
            site_stats[site_alias] = stats

    # ============================================================
    # RESUMO FINAL
    # ============================================================
    logger.info("\n" + "="*60)
    logger.info("RESUMO FINAL")
    logger.info("="*60)

    total_questions = 0
    total_answers = 0
    total_comments = 0

    for site, stats in site_stats.items():
        logger.info(f"\n{site}:")
        logger.info(f"  - Perguntas: {stats['questions']}")
        logger.info(f"  - Respostas: {stats['answers']}")
        logger.info(f"  - Comentários: {stats['comments']}")

        total_questions += stats['questions']
        total_answers += stats['answers']
        total_comments += stats['comments']

    logger.info(f"\n{'='*60}")
    logger.info(f"TOTAL GERAL:")
    logger.info(f"  - Perguntas: {total_questions}")
    logger.info(f"  - Respostas: {total_answers}")
    logger.info(f"  - Comentários: {total_comments}")
    logger.info(
        f"  - TOTAL DE REGISTROS: {total_questions + total_answers + total_comments}")
    logger.info(f"{'='*60}\n")

    logger.info(f"✓ Processo concluído! Arquivo gerado: {CONNECTED_POSTS}")


if __name__ == "__main__":
    main()
