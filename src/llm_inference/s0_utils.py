from functools import lru_cache
import pandas as pd
import json
from langchain_ollama import ChatOllama
from tqdm import tqdm

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import PROMPTS_DIR


@lru_cache(maxsize=None)
def _load_prompt_from_file(filename: str) -> str:
    """
    Carrega o conteúdo de um prompt de um arquivo de texto.

    Args:
        filename: O nome do arquivo na pasta de prompts (ex: 'anderson_v1.txt').

    Returns:
        O conteúdo do arquivo como uma string.
    """
    try:
        file_path = PROMPTS_DIR / filename
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(
            f"Erro: O arquivo de prompt '{filename}' não foi encontrado em '{PROMPTS_DIR}'.")
        raise


def judge_code_analysis() -> str:
    return _load_prompt_from_file("judge_code_v1.txt")


def hierarquical_code_anylisis() -> str:
    return _load_prompt_from_file("hierarquical_in_code_v1.txt")


# s2, s3

def get_processed_ids(filepath, id_column='post_id'):
    """Reads an output file and returns a set of already processed IDs."""
    if not os.path.exists(filepath):
        return set()
    try:
        df = pd.read_json(filepath, lines=True)
        if id_column in df.columns:
            return set(df[id_column].dropna().unique())
        else:
            return set()
    except ValueError:
        return set()


def load_data(filepath):
    """Loads data from a JSON file, supporting both standard and JSONL formats."""
    if not os.path.exists(filepath):
        print(f"Error: The file {filepath} was not found.")
        return []
    
    try:
        df = pd.read_json(filepath, lines=False)
    except (ValueError, TypeError):
        df = pd.read_json(filepath, lines=True)
        
    return df.to_dict('records')


def load_csv_data(filepath):
    """Loads data from a CSV file."""
    if not os.path.exists(filepath):
        print(f"Error: The file {filepath} was not found.")
        return []
    
    df = pd.read_csv(filepath)
    df = df[df['type'] == 'question']
    return df.to_dict('records')


def append_to_jsonl(data, filepath):
    """Appends a dictionary to a JSONL file."""
    df_response = pd.DataFrame([data])
    mode = 'a' if os.path.exists(filepath) else 'w'
    with open(filepath, mode) as f:
        f.write(df_response.to_json(orient='records', lines=True))


def run_pipeline_judge(input_file, output_file, prompt_template, 
                 process_case_func, id_column='post_id', limit=0, 
                 model_name="gemma3:1b", temperature=0, description="Processing",
                 data_loader=load_data
):
    """A general pipeline for processing data using an LLM."""
    all_cases = data_loader(input_file)
    processed_ids = get_processed_ids(output_file, id_column)

    cases_to_process = [case for case in all_cases if case.get(id_column) not in processed_ids]
    if limit:
        cases_to_process = cases_to_process[:limit]

    total = len(cases_to_process)
    model = ChatOllama(model=model_name, temperature=temperature, format='json')

    for case in tqdm(cases_to_process, total=total, desc=description):
        item_id = case.get(id_column)
        if not item_id:
            continue

        prompt_inputs = process_case_func(case)
        
        if prompt_inputs is None:
            continue
        
        formatted_prompt = prompt_template
        for key, value in prompt_inputs.items():
            formatted_prompt = formatted_prompt.replace(f"{{{{{key}}}}}", str(value))

        raw_response = model.invoke(formatted_prompt)
        try:
            response = json.loads(raw_response.content)
        except json.JSONDecodeError:
            print(f"Error decoding JSON for item {item_id}.")
            print(f"Raw response: {raw_response.content}")
            continue

        response[id_column] = item_id
        append_to_jsonl(response, output_file)


def run_pipeline_code_analysis(input_file, output_file, prompt_template, 
                 process_case_func, id_column='post_id', limit=0, 
                 model_name="gemma3:1b", temperature=0, description="Processing",
                 data_loader=load_data
):
    """A general pipeline for processing data using an LLM, filtering for 'question' type posts."""
    all_cases = data_loader(input_file)
    
    # Filter for questions
    cases_questions = [case for case in all_cases if case.get('type') == 'question']
    
    processed_ids = get_processed_ids(output_file, id_column)

    cases_to_process = [case for case in cases_questions if case.get(id_column) not in processed_ids]
    if limit:
        cases_to_process = cases_to_process[:limit]

    total = len(cases_to_process)
    model = ChatOllama(model=model_name, temperature=temperature, format='json')

    for case in tqdm(cases_to_process, total=total, desc=description):
        item_id = case.get(id_column)
        if not item_id:
            continue

        prompt_inputs = process_case_func(case)
        
        if prompt_inputs is None:
            continue
        
        formatted_prompt = prompt_template
        for key, value in prompt_inputs.items():
            formatted_prompt = formatted_prompt.replace(f"{{{{{key}}}}}", str(value))

        raw_response = model.invoke(formatted_prompt)
        try:
            response = json.loads(raw_response.content)
        except json.JSONDecodeError:
            print(f"Error decoding JSON for item {item_id}.")
            print(f"Raw response: {raw_response.content}")
            continue

        response[id_column] = item_id
        append_to_jsonl(response, output_file)
