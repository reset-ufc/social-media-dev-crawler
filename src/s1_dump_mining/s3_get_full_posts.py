from utils_global import (
    safe_date,
    get_logger,
    extract_tag_list,
    ensure_parent_dir,
    stream_posts_from_7z
)
from paths import DUMP, MERGED_TAGS, CONNECTED_POSTS, SITES
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
    "title", "body", "site", "id", "type"
]


def get_all_related_tags():
    """
    Read all related tags from the merged tags file (MERGED_TAGS).
    This file should be manually created by merging the final tag files
    from the previous processing steps.
    """
    try:
        df = pd.read_csv(MERGED_TAGS)
        related_tags = set(df['tag'])
        logger.info(
            f"Total related tags loaded from merged file: {len(related_tags)}")
        return related_tags
    except FileNotFoundError:
        logger.error(f"Merged tags file not found: {MERGED_TAGS}")
        logger.error("Please create this file manually by merging the tag files from previous steps.")
        return set()
    except Exception as e:
        logger.error(f"Error reading merged tags file: {e}")
        return set()


def initialize_csv():
    """Create output CSV with header."""
    ensure_parent_dir(CONNECTED_POSTS)
    with open(CONNECTED_POSTS, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(POST_FEATURES)


def append_batch_to_csv(batch):
    """Write a batch of records to CSV."""
    if not batch:
        return
    with open(CONNECTED_POSTS, "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(batch)


def process_site_unified(site_alias, site_name, related_tags):
    """
    Process a site in THREE optimized passes:
    1. Identify relevant questions (PostTypeId=1)
    2. Collect answers to these questions (PostTypeId=2)
    3. Collect comments from questions and answers

    Returns processing statistics.

    IMPORTANT: question_id now uses "site_alias:id" format to avoid conflicts between sites.
    """
    archive_path = os.path.join(DUMP, site_name)

    if not os.path.exists(archive_path):
        logger.warning(f"File not found: {archive_path}")
        return None

    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {site_alias}")
    logger.info(f"{'='*60}")

    # Data structures to store information
    # question_id_with_site (site:id) -> question attributes
    relevant_questions = {}
    answers_data = []  # list of answer attributes
    answer_id_to_question_id = {}  # maps answer_id original -> question_id_with_site
    posts_to_track = set()  # Original IDs of questions and answers to track comments
    # original post_id -> comment count
    comment_counter = defaultdict(int)
    comments_data = []  # list of comment attributes
    # maps original ID -> question_id_with_site (site:id)
    id_to_question_with_site = {}

    # PASS 1: Identify relevant questions
    logger.info("Phase 1/3: Identifying relevant questions...")
    try:
        with stream_posts_from_7z(archive_path, "Posts.xml") as context:
            for _, elem in context:
                if elem.tag != "row":
                    continue

                # Only questions
                if elem.attrib.get("PostTypeId") != "1":
                    elem.clear()
                    continue

                # Check if it has related tags
                tags_field = elem.attrib.get("Tags", "")
                if not tags_field:
                    elem.clear()
                    continue

                post_tags = set(extract_tag_list(tags_field))

                # If it has intersection with related tags
                if not related_tags.isdisjoint(post_tags):
                    question_id_original = elem.attrib.get("Id")
                    question_id_with_site = f"{site_alias}:{question_id_original}"

                    # Store mapping from original ID to ID with site
                    id_to_question_with_site[question_id_original] = question_id_with_site

                    # Format accepted_answer_id also with site prefix, if it exists
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
                        'title': elem.attrib.get("Title", ""),
                        'body': elem.attrib.get("Body", ""),
                        'id_original': question_id_original,
                    }
                    posts_to_track.add(question_id_original)

                elem.clear()

        logger.info(
            f"  → Found {len(relevant_questions)} relevant questions")

    except Exception as e:
        logger.error(f"Error in Phase 1 ({site_alias}): {e}", exc_info=True)
        return None

    # If no questions found, no need to continue
    if not relevant_questions:
        logger.info(f"  → No relevant questions found. Skipping site.")
        return {
            'questions': 0,
            'answers': 0,
            'comments': 0
        }

    # PASS 2: Collect answers to relevant questions
    logger.info("Phase 2/3: Collecting answers...")
    try:
        with stream_posts_from_7z(archive_path, "Posts.xml") as context:
            for _, elem in context:
                if elem.tag != "row":
                    continue

                # Only answers
                if elem.attrib.get("PostTypeId") != "2":
                    elem.clear()
                    continue

                parent_id_original = elem.attrib.get("ParentId")

                # If the answer belongs to a relevant question
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

                    # Map original answer -> question with site and add to tracking
                    answer_id_to_question_id[answer_id_original] = question_id_with_site
                    posts_to_track.add(answer_id_original)

                elem.clear()

        logger.info(f"  → Found {len(answers_data)} answers")

    except Exception as e:
        logger.error(f"Error in Phase 2 ({site_alias}): {e}", exc_info=True)
        return None

    # PASS 3: Collect comments from questions and answers
    logger.info("Phase 3/3: Collecting comments...")
    try:
        with stream_posts_from_7z(archive_path, "Comments.xml") as context:
            for _, elem in context:
                if elem.tag != "row":
                    continue

                post_id_original = elem.attrib.get("PostId")

                # If it's a comment on a relevant question or answer
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

        logger.info(f"  → Found {len(comments_data)} comments")

    except Exception as e:
        logger.error(f"Error in Phase 3 ({site_alias}): {e}", exc_info=True)
        return None

    logger.info("Assembling final batch...")
    final_batch = []

    # 1. Add all questions
    for qid_with_site, q in relevant_questions.items():
        final_batch.append([
            site_alias,
            q['tags'],
            qid_with_site,  # question_id with site:id format
            q['accepted_answer_id'],  # already in site:id format if exists
            q['answer_count'],
            q['creation_date'],
            q['last_activity_date'],
            q['last_edit_date'],
            q['owner_id'],
            q['score'],
            q['view_count'],
            # comment count using original ID
            comment_counter.get(q['id_original'], 0),
            q['title'],
            q['body'],
            site_name,
            qid_with_site,  # id with site:id format
            "question"
        ])

    # 2. Add all answers
    for a in answers_data:
        final_batch.append([
            site_alias,
            "",  # answers don't have tags
            a['parent_id'],  # question_id with site:id format
            "",  # accepted_answer_id (not applicable)
            "",  # answer_count (not applicable)
            a['creation_date'],
            a['last_activity_date'],
            a['last_edit_date'],
            a['owner_id'],
            a['score'],
            "",  # view_count (not applicable)
            # using original ID for counting
            comment_counter.get(a['answer_id_original'], 0),
            "",  # title (not applicable)
            a['body'],
            site_name,
            a['answer_id'],  # id with site:id format
            "answer"
        ])

    # 3. Add all comments
    for c in comments_data:
        post_id_original = c['post_id_original']

        # Determine which question the comment belongs to
        question_id = (id_to_question_with_site.get(post_id_original) or
                       answer_id_to_question_id.get(post_id_original))

        if question_id:
            final_batch.append([
                site_alias,
                "",  # comments don't have tags
                question_id,  # question_id with site:id format
                "",  # non-applicable fields
                "",
                c['creation_date'],
                "",  # last_activity_date (not applicable)
                "",  # last_edit_date (not applicable)
                c['user_id'],
                c['score'],
                "",  # view_count (not applicable)
                "",  # comment_count (not applicable)
                "",  # title (not applicable)
                c['text'],
                site_name,
                c['comment_id'],  # id with site:id format
                "comment"
            ])

    append_batch_to_csv(final_batch)
    logger.info(f"✓ Batch written successfully!")

    return {
        'questions': len(relevant_questions),
        'answers': len(answers_data),
        'comments': len(comments_data)
    }


def main():
    """Main function that coordinates the entire process."""
    logger.info("="*60)
    logger.info("UNIFIED EXTRACTION OF POSTS AND RELATED ELEMENTS")
    logger.info("="*60)

    # Load related tags from merged file
    logger.info(f"\nReading merged tags file: {MERGED_TAGS}")
    logger.info("Note: This file should be manually created by merging")
    logger.info("      the final tag files from previous processing steps.")
    
    related_tags = get_all_related_tags()
    if not related_tags:
        logger.error("No related tags found. Aborting.")
        logger.error(f"Please ensure {MERGED_TAGS} exists and contains a 'tag' column.")
        return

    initialize_csv()

    site_stats = {}

    for site_alias, site_name in SITES.items():
        stats = process_site_unified(site_alias, site_name, related_tags)

        if stats:
            site_stats[site_alias] = stats

    # ============================================================
    # FINAL SUMMARY
    # ============================================================
    logger.info("\n" + "="*60)
    logger.info("FINAL SUMMARY")
    logger.info("="*60)

    total_questions = 0
    total_answers = 0
    total_comments = 0

    for site, stats in site_stats.items():
        logger.info(f"\n{site}:")
        logger.info(f"  - Questions: {stats['questions']}")
        logger.info(f"  - Answers: {stats['answers']}")
        logger.info(f"  - Comments: {stats['comments']}")

        total_questions += stats['questions']
        total_answers += stats['answers']
        total_comments += stats['comments']

    logger.info(f"\n{'='*60}")
    logger.info(f"OVERALL TOTAL:")
    logger.info(f"  - Questions: {total_questions}")
    logger.info(f"  - Answers: {total_answers}")
    logger.info(f"  - Comments: {total_comments}")
    logger.info(
        f"  - TOTAL RECORDS: {total_questions + total_answers + total_comments}")
    logger.info(f"{'='*60}\n")

    logger.info(f"✓ Process completed! File generated: {CONNECTED_POSTS}")


if __name__ == "__main__":
    main()