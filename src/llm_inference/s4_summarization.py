import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_global import get_logger, ensure_parent_dir
from paths import *
import json
import pandas as pd
from collections import defaultdict, Counter
from pathlib import Path

logger = get_logger(__name__)


def load_json_array(path: Path):
    """Carrega JSON ou JSONL)."""
    if not path.exists():
        logger.warning(f"Arquivo JSON não encontrado: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        try:
            if content.startswith("["):
                return json.loads(content)
            else:
                return [json.loads(line) for line in content.splitlines() if line.strip()]
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao ler {path.name}: {e}")
            return []


def summarize_combined(misuse_data, judge_data):
    """Gera sumarização combinando misuse e judgement."""
    all_data = misuse_data + judge_data
    if not all_data:
        return "Nenhum dado encontrado.\n", pd.DataFrame()

    total_posts = len(all_data)
    misuse_cases = [x for x in all_data if x.get("has_misuse")]
    misuse_count = len(misuse_cases)
    non_misuse_count = total_posts - misuse_count

    # Contagem por site
    site_counts_misuse = Counter(x.get("site", "unknown") for x in misuse_cases)
    site_counts_nonmisuse = Counter(x.get("site", "unknown") for x in all_data if not x.get("has_misuse"))

    # Categorias e subtipos
    categories = defaultdict(Counter)
    rows = []
    for case in all_data:
        qid = case.get("question_id")
        site = case.get("site")
        has_misuse = case.get("has_misuse", False)
        if has_misuse:
            for m in case.get("misuses", []):
                cat = m.get("category", "Unknown")
                sub = m.get("subtype", "N/A")
                categories[cat][sub] += 1
                rows.append({
                    "question_id": qid,
                    "site": site,
                    "category": cat,
                    "subtype": sub,
                    "has_misuse": True
                })
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
    lines.append("s4 summarization \n")
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

    df = pd.DataFrame(rows)
    return "\n".join(lines) + "\n", df


def main():
    misuse_data = load_json_array(MISUSE_CASES_CODES)
    judge_data = load_json_array(JUDGEMENT_CODES)

    summary_text, df = summarize_combined(misuse_data, judge_data)

    # Caminhos de saída
    log_path = LLM_INFERENCE / "combined_summary.log"
    csv_path = LLM_INFERENCE / "combined_summary.csv"

    ensure_parent_dir(log_path)

    # Salva log 
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

    # Salva CSV 
    if not df.empty:
        df.to_csv(csv_path, index=False)

    logger.info(f"Sumarização combinada concluída.")
    logger.info(f"Log salvo em: {log_path}")
    logger.info(f"CSV salvo em: {csv_path}")

if __name__ == "__main__":
    main()
