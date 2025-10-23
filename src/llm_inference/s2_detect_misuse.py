import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import json
from langchain_ollama import ChatOllama
from tqdm import tqdm

from paths import PREPROCESSED_POSTS, MISUSE_CASES_CODES
from llm_inference.s0_prompts import hierarquical_code_anylisis
from llm_inference.s1_make_llm_input import code_analyze_string, get_post_metadata


def load_existing_cases(file_path):
    """Loads existing cases from a JSON or JSONL file."""
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            # Try to load as a single JSON array
            data = json.load(f)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            # If it fails, assume it's JSONL
            f.seek(0)
            cases = []
            for line in f:
                if line.strip():
                    try:
                        cases.append(json.loads(line))
                    except json.JSONDecodeError:
                        print(f"Warning: Could not decode line: {line}")
                        continue
            return cases

def load_preprocessed():
    try:
        df = pd.read_csv(PREPROCESSED_POSTS)
        df = df[df['type'] == 'question']
        post_ids = df['question_id'].tolist()
        return post_ids
    except FileNotFoundError:
        print(f"Error: The file {PREPROCESSED_POSTS} was not found.")
        return []
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")
        return []


def run_code_pipeline(template, limit=0):
    post_ids = load_preprocessed()
    
    # Load already processed cases and get their IDs
    existing_cases = load_existing_cases(MISUSE_CASES_CODES)
    processed_post_ids = {case.get('post_id') for case in existing_cases}

    # Filter out already processed posts
    posts_to_process = [pid for pid in post_ids if pid not in processed_post_ids]
    if limit:
        posts_to_process = posts_to_process[0:limit]

    total = len(posts_to_process)
    new_cases = []

    for post_id in tqdm(posts_to_process, total=total, desc="Analysing codes"):
        model = ChatOllama(model="gemma3:1b", temperature=0, format='json')

        code_input = code_analyze_string(str(post_id))
        metadata_input = get_post_metadata(str(post_id))

        if not code_input:
            print(f"No code found for post_id: {post_id}")
            continue
        
        try:
            formatted_prompt = template.replace("{{codes}}", code_input).replace("{{post_metadata}}", metadata_input)
            raw_response = model.invoke(formatted_prompt)
            response = json.loads(raw_response.content)

            response['post_id'] = post_id
            new_cases.append(response)

        except Exception as e:
            print(f"Error processing post_id {post_id}: {e}")
            continue
    
    # Combine old and new cases
    all_cases = existing_cases + new_cases

    # Write the entire list back to the file as a single JSON array
    with open(MISUSE_CASES_CODES, 'w', encoding='utf-8') as f:
        json.dump(all_cases, f, indent=2)
    
    print(f"\nFinished processing. Added {len(new_cases)} new cases. Total cases: {len(all_cases)}.")


if __name__ == "__main__":
    run_code_pipeline(
        hierarquical_code_anylisis(), 3
    )