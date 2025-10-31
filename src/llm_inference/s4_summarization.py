import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  

from utils_global import get_logger, ensure_parent_dir
from paths import *
import json
from collections import Counter
import pandas as pd
from pathlib import Path

logger = get_logger(__name__)


def summarize_misuse(input_path, output_path):
    """Gera um resumo dos casos de misuse detectados pela LLM."""
    if not input_path.exists():
        logger.error(f"Arquivo JSON não encontrado: {input_path}")
        return

    logger.info(f"Lendo arquivo de resultados: {input_path}")

    misuse_cases = []

    # Suporte para JSON (com [ ... ]) e JSONL (um objeto por linha)
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        try:
            if content.startswith("["):
                misuse_cases = json.loads(content)
            else:
                misuse_cases = [
                    json.loads(line)
                    for line in content.splitlines()
                    if line.strip()
                ]
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao ler arquivo JSON: {e}")
            return

    if not misuse_cases:
        logger.error("Nenhum dado foi carregado. Verifique o arquivo JSON.")
        return

    total_posts = len(misuse_cases)
    misuse_count = sum(1 for x in misuse_cases if x.get("has_misuse") is True)
    non_misuse_count = total_posts - misuse_count

    # Extrair todos os misuses com categoria e subtipo
    all_misuses = [
        m
        for case in misuse_cases
        if case.get("has_misuse")
        for m in case.get("misuses", [])
    ]

    category_counts = Counter(m["category"] for m in all_misuses if "category" in m)
    subtype_counts = Counter(m["subtype"] for m in all_misuses if "subtype" in m)

    # Os tipos (categoria + subtipo)
    misuse_types = [f"{m.get('category')} - {m.get('subtype')}" for m in all_misuses]
    type_counts = Counter(misuse_types)

    # DataFrames principais
    df_summary = pd.DataFrame([
        {"metric": "total_posts", "value": total_posts},
        {"metric": "misuse_count", "value": misuse_count},
        {"metric": "non_misuse_count", "value": non_misuse_count},
        {"metric": "misuse_ratio", "value": f"{(misuse_count / total_posts * 100):.2f}%"},
        {"metric": "distinct_categories", "value": len(category_counts)},
        {"metric": "distinct_subtypes", "value": len(subtype_counts)},
        {"metric": "distinct_misuse_types", "value": len(type_counts)},
    ])

    df_types = pd.DataFrame(type_counts.items(), columns=["misuse_type", "count"]).sort_values(by="count", ascending=False)
    df_categories = pd.DataFrame(category_counts.items(), columns=["category", "count"]).sort_values(by="count", ascending=False)
    df_subtypes = pd.DataFrame(subtype_counts.items(), columns=["subtype", "count"]).sort_values(by="count", ascending=False)

    # Posts com misuse
    df_with_misuse = pd.DataFrame([
        {
            "question_id": x.get("question_id"),
            "site": x.get("site"),
            "summary": x.get("summary", "").strip(),
            "categories": "; ".join(set(m["category"] for m in x.get("misuses", []))) if x.get("misuses") else "",
            "subtypes": "; ".join(set(m["subtype"] for m in x.get("misuses", []))) if x.get("misuses") else "",
        }
        for x in misuse_cases if x.get("has_misuse")
    ])

    ensure_parent_dir(output_path)

    # Exportar para CSV
    df_summary.to_csv(output_path, index=False)
    df_types.to_csv(output_path.with_name("misuse_types.csv"), index=False)
    df_categories.to_csv(output_path.with_name("categories.csv"), index=False)
    df_subtypes.to_csv(output_path.with_name("subtypes.csv"), index=False)
    
    misuse_csv_path = output_path.with_name("posts_with_misuse.csv")
    df_with_misuse.to_csv(misuse_csv_path, index=False)

    # Logs
    logger.info("===== SUMARIZAÇÃO CONCLUÍDA =====")
    logger.info(f"Total de posts analisados: {total_posts}")
    logger.info(f"Total com misuse: {misuse_count}")
    logger.info(f"Total sem misuse: {non_misuse_count}")
    logger.info(f"Categorias distintas: {len(category_counts)}")
    logger.info(f"Subtipos distintos: {len(subtype_counts)}")
    logger.info(f"Arquivo de resumo salvo em: {output_path}")
    logger.info(f"Lista detalhada dos posts com misuse salva em: {misuse_csv_path}")

if __name__ == "__main__":
    summarize_misuse(MISUSE_CASES_CODES, MISUSE_SUMMARY)
