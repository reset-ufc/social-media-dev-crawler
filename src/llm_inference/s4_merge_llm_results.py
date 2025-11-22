import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_global import ensure_parent_dir
from paths import *
import json
from llm_inference.s2_llm_chain import load_json_data


def get_judge_misuses(judge_question):
    """Busca a lista de misuses no objeto de julgamento, que pode ter chaves inconsistentes."""
    possible_keys = ["judgment", "judge", "misuse_evaluations", "evaluation", "evaluations", "misuse_evaluation"]
    for key in possible_keys:
        if key in judge_question and isinstance(judge_question[key], list):
            return judge_question[key]
    return []


def merge_results(misuse_data, judge_data, diff_threshold=DIF_CONFIDENCE_THRESHOLD):
    """
    Compara os resultados da análise e do julgamento, gerando um resultado consolidado.
    A concordância ocorre se a avaliação do juiz for consistente com a da inferência.
    - Se inferência aponta misuse: a diferença entre a confiança da inferência e a média da
      validação do juiz deve ser menor que o limiar.
    - Se inferência não aponta misuse: a média da validação do juiz deve ser menor que o limiar,
      indicando que o juiz também não viu um misuse claro.
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
        infer_misuses_map = {m.get("code_index"): m for m in infer_misuses if isinstance(m, dict) and m.get("code_index")}
        
        judge_misuses_list = get_judge_misuses(judge_question)
        
        agreed_codes = []
        
        # Itera sobre todos os códigos que o juiz analisou
        for judge_misuse in judge_misuses_list:
            code_index = judge_misuse.get("code_index")
            if not code_index:
                continue

            misuse_validity = judge_misuse.get("misuse_validity")
            classification_validity = judge_misuse.get("classification_validity")

            # Ignora se o juiz não forneceu valores válidos
            if not all(isinstance(v, (int, float)) for v in [misuse_validity, classification_validity]):
                continue
            
            avg_validity = (misuse_validity + classification_validity) / 2.0
            
            infer_misuse = infer_misuses_map.get(code_index)

            if infer_misuse:
                # Caso 1: Inferência encontrou um misuse para este código.
                confidence = infer_misuse.get("confidence")
                if not isinstance(confidence, (int, float)):
                    continue

                # Concordância se a confiança da inferência não for muito maior que a validação do juiz.
                if (confidence - avg_validity) < diff_threshold:
                    code_obj = {
                        "code_index": infer_misuse.get("code_index"),
                        "categories": infer_misuse.get("category") or infer_misuse.get("categories"),
                        "subtypes": infer_misuse.get("subtype") or infer_misuse.get("subtypes"),
                        "infer_confidence": confidence,
                        "misuse_validity": misuse_validity,
                        "classification_validity": classification_validity,
                        "infer_evidence": infer_misuse.get("evidence"),
                        "infer_rationale": infer_misuse.get("rationale"),
                        "judge_rationale": judge_misuse.get("rationale")
                    }
                    agreed_codes.append({k: v for k, v in code_obj.items() if v is not None})
            
            else:
                # Caso 2: Inferência NÃO encontrou misuse para este código.
                # A confidence da inferência de que HÁ um misuse é 0.
                # O usuário pediu para considerar a confidence de que NÃO HÁ misuse como 1.
                # A concordância ocorre se o juiz também não apontar um misuse (avg_validity baixo).
                # abs(0 - avg_validity) < diff_threshold  => avg_validity < diff_threshold
                if avg_validity < diff_threshold:
                    # Concordância de que não há misuse.
                    code_obj = {
                        "code_index": code_index,
                        "misuse_validity": misuse_validity,
                        "classification_validity": classification_validity,
                        "judge_rationale": judge_misuse.get("rationale")
                    }
                    agreed_codes.append({k: v for k, v in code_obj.items() if v is not None})

        # Determina o status final da questão com base nos códigos acordados
        has_misuse_in_agreed = any(c.get("categories") for c in agreed_codes)
        
        question_output = {
            "question_id": qid,
            "site": infer_question.get("site", ""),
            "has_misuse": has_misuse_in_agreed,
            "codes": agreed_codes
        }
        merged_questions_output.append(question_output)

        if question_output["has_misuse"]:
            questions_with_merged_codes += 1
            # Conta apenas os códigos que são misuses
            total_merged_codes += len([c for c in agreed_codes if c.get("categories")])

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
    main(FLAT_CODE_ANALYSIS, FLAT_CODE_JUDGEMENT,
           FLAT_MERGED_SUMMARY, FLAT_MERGED_LLM_RESULTS)
