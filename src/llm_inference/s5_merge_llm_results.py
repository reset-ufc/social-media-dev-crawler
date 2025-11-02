import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_global import get_logger, ensure_parent_dir
from paths import *
import json
import pandas as pd
from pathlib import Path

logger = get_logger(__name__)


def load_json_array(path: Path):
    """Carrega JSON (com [ ... ]) ou JSONL (um por linha)."""
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


def merge_results(misuse_data, judge_data, tolerance=0.1):
    """Compara resultados do inferente e do juiz."""
    misuse_map = {x["question_id"]: x for x in misuse_data if "question_id" in x}
    judge_map = {x["question_id"]: x for x in judge_data if "question_id" in x}

    merged = []
    valid_count = 0
    invalid_count = 0

    for qid, infer_case in misuse_map.items():
        judge_case = judge_map.get(qid)
        if not judge_case:
            continue

        infer_conf = infer_case.get("confidence", 1.0)
        judge_conf = judge_case.get("confidence", 1.0)
        infer_misuse = infer_case.get("has_misuse", False)
        judge_misuse = judge_case.get("has_misuse", False)

        # Verifica se estão próximos em confiança e mesma decisão
        confidence_diff = abs(infer_conf - judge_conf)
        same_decision = infer_misuse == judge_misuse
        valid = same_decision and confidence_diff <= tolerance

        merged.append({
            "question_id": qid,
            "site": infer_case.get("site", ""),
            "infer_has_misuse": infer_misuse,
            "judge_has_misuse": judge_misuse,
            "infer_confidence": infer_conf,
            "judge_confidence": judge_conf,
            "confidence_diff": round(confidence_diff, 3),
            "same_decision": same_decision,
            "valid_pair": valid
        })

        if valid:
            valid_count += 1
        else:
            invalid_count += 1

    df = pd.DataFrame(merged)
    total = len(df)
    ratio_valid = (valid_count / total * 100) if total > 0 else 0

    summary_lines = [
        "s5 merge llm results\n",
        f"total paired questions: {total}",
        f"valid pairs: {valid_count}",
        f"invalid pairs: {invalid_count}",
        f"taxa de alinhamento: {ratio_valid:.2f}%\n"
    ]

    return "\n".join(summary_lines), df


def main():
    misuse_data = load_json_array(MISUSE_CASES_CODES)
    judge_data = load_json_array(JUDGEMENT_CODES)

    summary_text, df = merge_results(misuse_data, judge_data)

    log_path = LLM_INFERENCE / "s5_merge_summary.log"
    csv_path = LLM_INFERENCE / "merged_results.csv"

    ensure_parent_dir(log_path)

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

    if not df.empty:
        df.to_csv(csv_path, index=False)

    logger.info("Merge concluído com sucesso.")
    logger.info(f"Resumo salvo em: {log_path}")
    logger.info(f"Dataset salvo em: {csv_path}")


if __name__ == "__main__":
    main()
