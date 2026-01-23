from dotenv import load_dotenv
import pandas as pd
from langchain_openai import ChatOpenAI

from gensim.models.ldamodel import LdaModel
import json
from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import *

load_dotenv()


class TopicInference(BaseModel):
    topic_id: int = Field(description="Index/ID of the topic")
    inferred_name: str = Field(
        description="Short name for the topic (2-5 words)")
    rationale: str = Field(description="Brief explanation of the topic name")


class TopicInferenceOutput(BaseModel):
    topics: List[TopicInference] = Field(
        description="List of inferred topic names with explanations")


def format_topics_for_llm(model: LdaModel, num_words: int = 20) -> str:
    """
    Extract topics from LDA model and format as readable text for LLM.

    Returns a formatted string of topics with their keywords and weights.
    This preprocessing improves LLM accuracy by presenting data clearly.
    """
    formatted_topics = []

    for topic_id in range(model.num_topics):
        top_terms = model.show_topic(topic_id, topn=num_words)
        top_terms = sorted(top_terms, key=lambda x: x[1], reverse=True)

        terms_str = ", ".join(
            [f'word: "{word}" weight: ({weight:.6f})' for word, weight in top_terms])
        formatted_topics.append(f"Topic {topic_id}: [{terms_str}]")
    return "\n".join(formatted_topics)


def _invoke_llm_inference(
    llm,
    prompt_template: str,
    prompt_variables: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generic function to invoke LLM inference for topic naming.

    Args:
        llm: LangChain LLM instance.
        prompt_template: The prompt template string.
        prompt_variables: A dictionary of variables to pass to the prompt.

    Returns:
        The parsed JSON output from the LLM.
    """
    prompt = PromptTemplate(
        input_variables=list(prompt_variables.keys()),
        template=prompt_template
    )
    parser = JsonOutputParser(pydantic_object=TopicInferenceOutput)
    chain = prompt | llm | parser

    print(f"Invoking LLM with variables: {list(prompt_variables.keys())}...")
    return chain.invoke(prompt_variables)


def infer_topic_names(model: LdaModel, llm, model_path: Path) -> dict:
    """
    Use LangChain + LLM to infer meaningful names for LDA topics.

    Args:
        model: Trained LDA model.
        llm: LangChain LLM instance.
        model_path: Path to the model directory.

    Returns a dictionary with inferred topic names and rationales.
    """
    prompt_path = model_path / LDA_TOPICS
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

    prompt_template = prompt_path.read_text(encoding='utf-8')
    formatted_topics = format_topics_for_llm(model)
    print(f"Formatted {model.num_topics} topics for LLM inference")

    return _invoke_llm_inference(
        llm,
        prompt_template,
        {"model_output": formatted_topics}
    )


def subtopics_inference(main_model_path: Path, llm, num_words: int = 20) -> dict:
    """
    Infer names for subtopics of a main topic.

    Args:
        main_model_path: Path to the main model folder.
        llm: LangChain LLM instance.
        num_words: Number of words to extract per subtopic.

    Returns a dict mapping submodel folder -> inference result.
    """
    models_root = main_model_path.parent

    ti_path = main_model_path / 'topic_inference.json'
    if not ti_path.exists():
        raise FileNotFoundError(f"topic_inference.json not found at {ti_path}")
    ti = pd.read_json(ti_path)

    meta_path = main_model_path / 'trained_lda.meta.json'
    if not meta_path.exists():
        raise FileNotFoundError(
            f"trained_lda.meta.json not found at {meta_path}")
    k = int(pd.read_json(meta_path, orient='index').T['num_topics'].item())

    prompt_file = PROMPTS_DIR / 'lda_subtopics.txt'
    if not prompt_file.exists():
        raise FileNotFoundError(
            f"Prompt file for subtopics not found at {prompt_file}")
    prompt_template = prompt_file.read_text(encoding='utf-8')

    results = {}
    for idx in range(k):
        submodel_folder = models_root / f't{idx}'
        if not submodel_folder.exists():
            print(f"Skipping missing submodel folder: {submodel_folder}")
            continue

        try:
            main_topic_name = ti.loc[idx]['topics']['topic_name']
        except Exception:
            main_topic_name = f"topic_{idx}"

        submodel = LdaModel.load(str(submodel_folder / 'trained_lda.model'))
        formatted_topics = format_topics_for_llm(submodel, num_words=num_words)

        print(
            f"Invoking LLM for submodel t{idx} (main_topic='{main_topic_name}')...")
        try:
            out = _invoke_llm_inference(
                llm,
                prompt_template,
                {"subtopic": main_topic_name, "model_output": formatted_topics}
            )
            results[f't{idx}'] = out

            out_path = submodel_folder / LDA_TOPIC_INFERENCE
            save_topic_inference(out, out_path)
            print(f"Saved subtopic inference to {out_path}")
        except Exception as e:
            print(f"LLM call failed for t{idx}: {e}")

    return results


def save_topic_inference(inference_result: dict, output_path: Path) -> None:
    """Save inferred topic names to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(output_path), 'w', encoding='utf-8') as f:
        json.dump(inference_result, f, indent=2, ensure_ascii=False)
    print(f"Topic inference saved to {output_path}")


def main_topic_inference(model_path, llm):
    model_path = Path(model_path)
    lda_model_path = model_path / TRAINED_LDA
    if not lda_model_path.exists():
        raise FileNotFoundError(
            f"Trained LDA model not found at {lda_model_path}")

    print("Loading trained LDA")
    model = LdaModel.load(str(lda_model_path))
    print(f"Model loaded. Number of topics: {model.num_topics}")

    inference_result = infer_topic_names(model, llm, model_path)
    save_topic_inference(inference_result, model_path / 'topic_inference.json')


if __name__ == '__main__':
    main_topic_inference(
        MODELS / 'main',
        llm=ChatOpenAI(model_name="gpt-5.2", temperature=0.7),
    )
    """subtopics_inference(
        MODELS / 'main',
        llm=ChatOpenAI(model_name="gpt-5.2", temperature=0.7),
    )"""
