import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from typing import List
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import PromptTemplate
from langchain_ollama import ChatOllama
import json
from gensim.models.ldamodel import LdaModel
from paths import *
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv
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

    # Get all topics from the model
    for topic_id in range(model.num_topics):
        # Get top words for this topic (word, weight) pairs
        top_terms = model.show_topic(topic_id, topn=num_words)
        top_terms = sorted(top_terms, key=lambda x: x[1], reverse=True)

        terms_str = ", ".join(
            [f"word: {word} weight: ({weight:.6f})" for word, weight in top_terms])
        formatted_topics.append(f"Topic {topic_id}: [{terms_str}]")
    return "\n".join(formatted_topics)


def infer_topic_names(model: LdaModel, llm, model_path) -> dict:
    """
    Use LangChain + LLM to infer meaningful names for LDA topics.

    Args:
        model: Trained LDA model
        llm: LangChain LLM instance (e.g., ChatOllama, ChatOpenAI)

    Returns a dictionary with inferred topic names and rationales.
    """
    # Load prompt template
    if not Path(model_path / LDA_TOPICS).exists():
        raise FileNotFoundError(f"Prompt file not found at {model_path / LDA_TOPICS}")

    with open(str(model_path / LDA_TOPICS), 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    # Format topics for input
    formatted_topics = format_topics_for_llm(model)
    print(f"Formatted {model.num_topics} topics for LLM inference")

    # Create LangChain prompt
    prompt = PromptTemplate(
        input_variables=["model_output"],
        template=prompt_template
    )

    # Create output parser
    parser = JsonOutputParser(pydantic_object=TopicInferenceOutput)

    # Build chain
    chain = prompt | llm | parser

    # Invoke chain
    print("Invoking LLM to infer topic names...")
    result = chain.invoke({"model_output": formatted_topics})

    return result


def save_topic_inference(inference_result: dict, output_path: Path) -> None:
    """Save inferred topic names to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(str(output_path), 'w', encoding='utf-8') as f:
        json.dump(inference_result, f, indent=2, ensure_ascii=False)

    print(f"Topic inference saved")


def main(model_path, llm):
    if not Path(model_path / TRAINED_LDA).exists():
        raise FileNotFoundError(
            f"Trained LDA model not found at {model_path / TRAINED_LDA}")

    print(f"Loading trained LDA")
    model = LdaModel.load(str(model_path / TRAINED_LDA))
    print(f"Model loaded. Number of topics: {model.num_topics}")

    # Infer topic names via LLM
    inference_result = infer_topic_names(model, llm, model_path)

    # Save results
    save_topic_inference(inference_result, Path(model_path / 'topic_inference.json'))


if __name__ == '__main__':
    main(
        MODELS / 'main',
        #llm=ChatOllama(model_name='deepseek-r1:32b', temperature=0.7),
        llm=ChatOpenAI(model_name="gpt-5.1", temperature=0.7),
        )
