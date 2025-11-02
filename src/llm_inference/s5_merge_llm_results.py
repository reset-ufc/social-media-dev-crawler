import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_global import get_logger, ensure_parent_dir
from paths import *
import json
import pandas as pd
from pathlib import Path

from llm_inference.s0_utils import load_data


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

    df_all = pd.DataFrame(merged)
    total = len(df_all)
    ratio_valid = (valid_count / total * 100) if total > 0 else 0

    summary_lines = [
        "s5 merge llm results\n",
        f"total paired questions: {total}",
        f"valid pairs: {valid_count}",
        f"invalid pairs: {invalid_count}",
        f"taxa de alinhamento: {ratio_valid:.2f}%\n"
    ]

    df_valid = df_all[df_all['valid_pair'] == True].reset_index(drop=True)
    return "\n".join(summary_lines), df_valid


def main():
    misuse_data = load_data(CODE_ANALYSIS)
    judge_data = load_data(CODE_JUDGEMENT)

    summary_text, df = merge_results(misuse_data, judge_data)

    with open(MERGE_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary_text)

    try:
        if not df.empty:
            with open(MERGED_LLM_RESULTS, 'w', encoding='utf-8') as f:
                f.write(df.to_json(orient='records', lines=True))
    except Exception:
        print(f'Erro ao salvar merged results em: {MERGED_LLM_RESULTS}')


if __name__ == "__main__":
    main()
