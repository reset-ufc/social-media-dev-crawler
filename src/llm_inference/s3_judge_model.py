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


def get_processed_post_ids():
    """Reads the output file and returns a set of already processed post IDs."""
    if not os.path.exists(MISUSE_CASES_CODES):
        return set()
    
    processed_ids = set()
    with open(MISUSE_CASES_CODES, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                if 'post_id' in data:
                    processed_ids.add(data['post_id'])
            except json.JSONDecodeError:
                # Ignore lines that are not valid JSON
                continue
    return processed_ids


def load_preprocessed():
    try:
        df = pd.read_csv(PREPROCESSED_POSTS)
        df = df[df['type'] == 'question']
        post_ids = df['question_id'].tolist()
        return post_ids
    except FileNotFoundError:
        print(f"Error: The file {PREPROCESSED_POSTS} was not found.")
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")


def run_code_pipeline(template, limit=0):
    """
    Executes a pipeline to analyze code snippets from posts for potential misuse.
    """
    post_ids = load_preprocessed()
    processed_post_ids = get_processed_post_ids()

    # Filter out already processed posts
    posts_to_process = [pid for pid in post_ids if pid not in processed_post_ids]
    if limit:
        posts_to_process = posts_to_process[0:limit]

    total = len(posts_to_process)

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
            
            df_response = pd.DataFrame([response])
            with open(MISUSE_CASES_CODES, 'a') as f:
                df_response.to_json(f, orient='records', lines=True)

        except Exception as e:
            # print(f"An error occurred while invoking the chain for post_id {post_id}: {e}")
            continue

if __name__ == "__main__":
    run_code_pipeline(
        hierarquical_code_anylisis(), 3
    )
