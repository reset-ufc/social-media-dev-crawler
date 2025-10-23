import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import json
from langchain_ollama import ChatOllama
from tqdm import tqdm

from paths import MISUSE_CASES_CODES, JUDGEMENT_CODES
from llm_inference.s0_prompts import judge_code_analysis
from llm_inference.s1_make_llm_input import code_analyze_string


def get_judged_post_ids():
    """Reads the output file and returns a set of already judged post IDs."""
    if not os.path.exists(JUDGEMENT_CODES):
        return set()
    
    judged_ids = set()
    with open(JUDGEMENT_CODES, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                if 'post_id' in data:
                    judged_ids.add(data['post_id'])
            except json.JSONDecodeError:
                continue
    return judged_ids


def load_misuse_cases():
    """Loads the misuse cases from the JSON file, supporting both standard and JSONL formats."""
    if not os.path.exists(MISUSE_CASES_CODES):
        print(f"Error: The file {MISUSE_CASES_CODES} was not found.")
        return []
    
    try:
        with open(MISUSE_CASES_CODES, 'r', encoding='utf-8') as f:
            # Try to load the whole file as a single JSON object/array
            return json.load(f)
    except json.JSONDecodeError:
        # If that fails, assume it's a JSON Lines file and read line by line
        cases = []
        with open(MISUSE_CASES_CODES, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return cases


def run_judge_pipeline(template, limit=0):
    misuse_cases = load_misuse_cases()
    judged_post_ids = get_judged_post_ids()

    # Filter out already judged posts
    cases_to_process = [case for case in misuse_cases if case.get('post_id') not in judged_post_ids]
    if limit:
        cases_to_process = cases_to_process[0:limit]

    total = len(cases_to_process)

    for case in tqdm(cases_to_process, total=total, desc="Judging analyses"):
        model = ChatOllama(model="gemma3:1b", temperature=0, format='json')

        post_id = case.get('post_id')
        if not post_id:
            continue

        code_input = code_analyze_string(str(post_id))
        analysis_input = json.dumps(case, indent=2)

        try:
            formatted_prompt = template.replace("{{codes}}", code_input).replace("{{analysis}}", analysis_input)
            raw_response = model.invoke(formatted_prompt)
            response = json.loads(raw_response.content)

            response['post_id'] = post_id

            df_response = pd.DataFrame([response])
            with open(JUDGEMENT_CODES, 'a') as f:
                df_response.to_json(f, orient='records', lines=True)

        except Exception as e:
            print(e)
            continue


if __name__ == "__main__":
    run_judge_pipeline(
        judge_code_analysis(), 10
    )
