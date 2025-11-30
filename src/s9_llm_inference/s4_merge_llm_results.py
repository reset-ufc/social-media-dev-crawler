import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_global import ensure_parent_dir
from paths import *
import json
from llm_inference.s2_llm_chain import load_json_data


def get_judge_misuses(judge_question):
    """Busca a lista de misuses no objeto de julgamento, que pode ter chaves inconsistentes."""
    possible_keys = ["judgment", "judge", "misuse_evaluations",
                     "evaluation", "evaluations", "misuse_evaluation"]
    for key in possible_keys:
        if key in judge_question and isinstance(judge_question[key], list):
            return judge_question[key]
    return []


def merge_results(misuse_data, judge_data, diff_threshold=DIF_CONFIDENCE_THRESHOLD):
    """
    Une as respostas do juiz e do inferente.
    Para cada código, se a confidencia entre as respostas não tiver diferença maior
    que o diff_threshold, então o código é adicionado a resposta final.
    Caso o campo misuses do infer estiver vazio, então considere sua cofidence como 1.

    Na resposta final, se houve ao menos um código em que teve concordancia,
    adicione agreement=True na resposta. Caso o infer retornou o campo misuse
    vazio e o juiz retornou um confidence alto o bastante, adicione também
    agreement=True, para dizer que ambos concordaram que não há misuse.
    """
    misuse_map = {x["question_id"]
        : x for x in misuse_data if "question_id" in x}
    judge_map = {x["question_id"]: x for x in judge_data if "question_id" in x}

    common_qids = misuse_map.keys() & judge_map.keys()

    merged_questions_output = []
    total_merged_codes = 0
    questions_with_merged_codes = 0
    veredict_counts = {"agree_misuse": 0, "agree_no_misuse": 0, "disagree": 0}

    for qid in common_qids:
        infer_question = misuse_map[qid]
        judge_question = judge_map[qid]

        # Mapa de misuses do inferente para acesso rápido pelo code_index
        infer_misuses = infer_question.get("misuses", [])
        infer_misuses_map = {m["code_index"]: m for m in infer_misuses if isinstance(
            m, dict) and "code_index" in m}

        # Lista de avaliações do juiz
        judge_evals = get_judge_misuses(judge_question)

        agreed_codes = []
        question_agreement = False

        # Itera sobre todas as avaliações do juiz para a questão
        for judge_eval in judge_evals:
            code_index = judge_eval.get("code_index")
            if not code_index:
                continue

            # Confiança do Juiz (considerando a média de validade como a confiança)
            misuse_validity = judge_eval.get("misuse_validity", 0)
            classification_validity = judge_eval.get(
                "classification_validity", 0)
            judge_confidence = (
                misuse_validity + classification_validity) / 2.0

            infer_misuse = infer_misuses_map.get(code_index)

            veredict = None
            within_threshold = False

            if infer_misuse:
                # Caso 1: Inferente encontrou um misuse.
                infer_confidence = infer_misuse.get("confidence", 0)
                diff = abs(judge_confidence - infer_confidence)
                # Verifica se a diferença de confiança está dentro do limiar
                if diff <= diff_threshold:
                    veredict = "agree_misuse"
                    within_threshold = True
                    question_agreement = True
                else:
                    veredict = "disagree"
            else:
                # Caso 2: Inferente NÃO encontrou misuse, sua confiança de que não há misuse é 1.
                infer_confidence = 1
                diff = abs(judge_confidence - 1)
                # Concordam se a confiança do juiz também for alta (próxima de 1).
                if diff <= diff_threshold:
                    veredict = "agree_no_misuse"
                    within_threshold = True
                    question_agreement = True
                else:
                    veredict = "disagree"

            if veredict:
                code_obj = {
                    "code_index": code_index,
                    "infer_confidence": infer_confidence,
                    "judge_confidence": judge_confidence,
                    "veredict": veredict
                }
                if infer_misuse:
                    code_obj.update({
                        "categories": infer_misuse.get("category") or infer_misuse.get("categories"),
                        "subtypes": infer_misuse.get("subtype") or infer_misuse.get("subtypes"),
                        "infer_evidence": infer_misuse.get("evidence"),
                        "infer_rationale": infer_misuse.get("rationale"),
                    })
                code_obj["judge_rationale"] = judge_eval.get("rationale")
                agreed_codes.append(
                    {k: v for k, v in code_obj.items() if v is not None})

        question_output = {
            "question_id": qid,
            "site": infer_question.get("site", ""),
            "codes": agreed_codes
        }
        merged_questions_output.append(question_output)

        if agreed_codes and any(c.get("veredict") == "agree_misuse" for c in agreed_codes):
            questions_with_merged_codes += 1
            total_merged_codes += sum(
                1 for c in agreed_codes if c.get("veredict") == "agree_misuse")

        # Contabilizar vereditos
        for code in agreed_codes:
            veredict = code.get("veredict")
            if veredict in veredict_counts:
                veredict_counts[veredict] += 1

    summary_lines = [
        "s4 merge llm results\n",
        f"Total unique questions analyzed (present in both files): {len(common_qids)}",
        f"Total merged codes (agreed and validated misuses): {total_merged_codes}",
        f"Total questions with at least one merged misuse code: {questions_with_merged_codes}",
        f"\nVeredito breakdown:",
        f"  - agree_misuse: {veredict_counts['agree_misuse']}",
        f"  - agree_no_misuse: {veredict_counts['agree_no_misuse']}",
        f"  - disagree: {veredict_counts['disagree']}\n"
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
            print(
                f'Erro ao salvar resultados mergeados em: {merged_llm_results}, erro: {e}')
    else:
        print("Nenhum dado mergeado para salvar.")


if __name__ == "__main__":
    main(HIER_CODE_FULL_CLASSIFICATION, HIER_CODE_JUDGEMENT,
         HIER_MERGED_SUMMARY, HIER_MERGED_LLM_RESULTS)
