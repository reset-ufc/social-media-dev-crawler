import pandas as pd
import os
from tqdm import tqdm
import json
from langchain_ollama import ChatOllama


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


def load_json_data(filepath):
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


def save_response(cases_to_process, total, description, id_column, process_case_func,
                  prompt_template, model, output_file):
    for case in tqdm(cases_to_process, total=total, desc=description):
        item_id = case.get(id_column)
        item_site = case.get('site')

        prompt_inputs = process_case_func(case)

        if prompt_inputs is None:
            continue

        formatted_prompt = prompt_template
        for key, value in prompt_inputs.items():
            formatted_prompt = formatted_prompt.replace(
                f"{{{{{key}}}}}", str(value))

        raw_response = model.invoke(formatted_prompt)
        try:
            response = json.loads(raw_response.content)
        except json.JSONDecodeError:
            print(f"Error decoding JSON for item {item_site}: {item_id}.")
            print(f"Raw response: {raw_response.content}")
            continue

        response[id_column] = item_id
        response['site'] = item_site
        append_to_jsonl(response, output_file)


def run_llm_chain(input_file, output_file, prompt_template,
                  process_case_func, id_column='question_id', limit=0,
                  model_name="gemma3:1b", temperature=0, description="Processing",
                  data_loader=load_json_data, filter_dict=None
                  ):
    """A general pipeline for processing data using an LLM."""
    all_cases = data_loader(input_file)

    if filter_dict:
        for key, value in filter_dict.items():
            all_cases = [case for case in all_cases if case.get(key) == value]

    processed_ids = get_processed_ids(output_file, id_column)
    cases_to_process = [case for case in all_cases if case.get(
        id_column) not in processed_ids]
    if limit:
        cases_to_process = cases_to_process[:limit]

    total = len(cases_to_process)
    model = ChatOllama(
        model=model_name, temperature=temperature, format='json')

    save_response(cases_to_process, total, description, id_column, process_case_func,
                  prompt_template, model, output_file)
