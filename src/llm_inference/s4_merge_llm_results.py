import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_global import ensure_parent_dir
from paths import *
import json
from llm_inference.s2_llm_chain import load_json_data


def get_judge_misuses(judge_question):
    """Busca a lista de misuses no objeto de julgamento, que pode ter chaves inconsistentes."""
    possible_keys = ["judge", "misuse_evaluations", "evaluation", "evaluations", "misuse_evaluation"]
    for key in possible_keys:
        if key in judge_question and isinstance(judge_question[key], list):
            return judge_question[key]
    return []


def merge_results(misuse_data, judge_data):
    """
    Compara os resultados da análise e do julgamento. A concordância ocorre quando um 'misuse'
    com o mesmo 'code_index' é encontrado em ambos os resultados e o juiz o valida com 'misuse_validity': 1.
    """
    misuse_map = {x["question_id"]: x for x in misuse_data if "question_id" in x}
    judge_map = {x["question_id"]: x for x in judge_data if "question_id" in x}

    common_qids = misuse_map.keys() & judge_map.keys()

    merged_questions_output = []
    total_merged_codes = 0
    questions_with_merged_codes = 0

    for qid in common_qids:
        infer_question = misuse_map[qid]
        judge_question = judge_map[qid]

        infer_misuses = infer_question.get("misuses", [])
        judge_misuses_list = get_judge_misuses(judge_question)

        if not infer_misuses or not judge_misuses_list:
            continue

        judge_validated_misuses_map = {
            m.get("code_index"): m
            for m in judge_misuses_list
            if m.get("code_index") and m.get("misuse_validity") == 1
        }

        if not judge_validated_misuses_map:
            continue

        merged_codes_for_question = []
        for infer_misuse in infer_misuses:
            code_index = infer_misuse.get("code_index")
            if code_index and code_index in judge_validated_misuses_map:
                judge_misuse = judge_validated_misuses_map[code_index]
                merged_codes_for_question.append({
                    "code_index": code_index,
                    "analysis_classification": infer_misuse,
                    "judgement_classification": judge_misuse,
                })

        if merged_codes_for_question:
            questions_with_merged_codes += 1
            total_merged_codes += len(merged_codes_for_question)
            merged_questions_output.append({
                "question_id": qid,
                "site": infer_question.get("site", ""),
                "codes": merged_codes_for_question
            })

    summary_lines = [
        "s5 merge llm results\n",
        f"Total unique questions analyzed (present in both files): {len(common_qids)}",
        f"Total merged codes (agreed and validated misuses): {total_merged_codes}",
        f"Total questions with at least one merged code: {questions_with_merged_codes}\n"
    ]

    return "\n".join(summary_lines), merged_questions_output


def main(misuse_data, judge_data, merge_summary, merged_llm_results):
    """
    Função principal para carregar os dados, executar o merge e salvar os resultados.
    """
    misuse_data = load_json_data(misuse_data)
    judge_data = load_json_data(judge_data)

    summary_text, merged_data = merge_results(misuse_data, judge_data)

    ensure_parent_dir(merge_summary)
    with open(merge_summary, "w", encoding="utf-8") as f:
        f.write(summary_text)
    
    print("--- Merge Summary ---")
    print(summary_text)

    if merged_data:
        try:
            ensure_parent_dir(merged_llm_results)
            with open(merged_llm_results, 'w', encoding='utf-8') as f:
                for item in merged_data:
                    f.write(json.dumps(item) + '\n')
            print(f"Resultados mergeados salvos em: {merged_llm_results}")
        except Exception as e:
            print(f'Erro ao salvar resultados mergeados em: {merged_llm_results}, erro: {e}')
    else:
        print("Nenhum dado mergeado para salvar.")


if __name__ == "__main__":
    main()
