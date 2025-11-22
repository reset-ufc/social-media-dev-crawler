import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_global import get_logger, ensure_parent_dir
from paths import *
import pandas as pd
from collections import defaultdict, Counter
from llm_inference.s2_llm_chain import load_json_data

logger = get_logger(__name__)


def summarize_analysis(misuse_data):
    if not misuse_data:
        return "Nenhum dado encontrado.\n"

    total_posts = len(misuse_data)
    misuse_cases = [x for x in misuse_data if x.get("has_misuse")]
    misuse_count = len(misuse_cases)
    non_misuse_count = total_posts - misuse_count

    # Contagem por site
    site_counts_misuse = Counter(x.get("site", "unknown") for x in misuse_cases)
    site_counts_nonmisuse = Counter(x.get("site", "unknown") for x in misuse_data if not x.get("has_misuse"))

    # Categorias e subtipos
    categories = defaultdict(Counter)
    rows = []
    failed_samples = []
    for case in misuse_data:
        qid = case.get("question_id")
        site = case.get("site")
        has_misuse = case.get("has_misuse", False)
        if has_misuse:
            for m in case.get("misuses", []):
                try:
                    cat = m.get("categories", "Unknown")
                    sub = m.get("subtypes", "N/A")
                    categories[cat][sub] += 1
                    rows.append({
                        "question_id": qid,
                        "site": site,
                        "category": cat,
                        "subtype": sub,
                        "has_misuse": True
                    })
                except AttributeError:
                    logger.warning(f"Amostra com erro de atributo em 'summarize_analysis' para site: {site}, qid: {qid}")
                    failed_samples.append({'site': site, 'question_id': qid})
        else:
            rows.append({
                "question_id": qid,
                "site": site,
                "category": "",
                "subtype": "",
                "has_misuse": False
            })

    # Logs
    lines = []
    lines.append("analysis summarization \n")
    lines.append(f"total posts: {total_posts}")
    lines.append(f"total misuse count: {misuse_count}\n")

    if site_counts_misuse:
        lines.append("site misuse count:")
        for site, count in site_counts_misuse.items():
            lines.append(f" - {site}: {count}")

    lines.append(f"\ntotal non misuse count: {non_misuse_count}")
    if site_counts_nonmisuse:
        lines.append("site non misuse count:")
        for site, count in site_counts_nonmisuse.items():
            lines.append(f" - {site}: {count}")

    lines.append("\nCategory & Subtypes count")
    for cat, subs in categories.items():
        total_cat = sum(subs.values())
        lines.append(f"{cat}: {total_cat}")
        for sub, sub_count in subs.items():
            lines.append(f" - {sub}: {sub_count}")

    if failed_samples:
        lines.append("\nAmostras que falharam na sumarização:")
        unique_failures = sorted(list(set((d['site'], d['question_id']) for d in failed_samples)))
        for site, qid in unique_failures:
            lines.append(f" - site: {site}, question_id: {qid}")

    return "\n".join(lines) + "\n"


def main(misuse_data, summary):
    misuse = load_json_data(misuse_data)
    summary_text = summarize_analysis(misuse)

    logger.info(summary_text)

    try:
        ensure_parent_dir(summary)
        with open(summary, 'w', encoding='utf-8') as f:
            f.write(summary_text)
    except Exception:
        logger.exception(f'Erro ao salvar o resumo em: {summary}')

if __name__ == "__main__":
    main()
