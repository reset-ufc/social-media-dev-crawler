import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from typing import List
from pydantic import BaseModel, Field
from langchain.output_parsers import JsonOutputParser
from langchain.prompts import PromptTemplate
from langchain_ollama import ChatOllama
import json
from gensim.models.ldamodel import LdaModel
from paths import TRAINED_LDA, LDA_TOPICS, TOPIC_INFERENCE


class TopicInference(BaseModel):
    topic_id: int = Field(description="Index/ID of the topic")
    inferred_name: str = Field(
        description="Short name for the topic (2-5 words)")
    rationale: str = Field(description="Brief explanation of the topic name")


class TopicInferenceOutput(BaseModel):
    topics: List[TopicInference] = Field(
        description="List of inferred topic names with explanations")


def format_topics_for_llm(model: LdaModel, num_words: int = 10) -> str:
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

        # Format: "Topic 0: [word1 (0.05), word2 (0.04), ...]"
        terms_str = ", ".join(
            [f"{word} ({weight:.4f})" for word, weight in top_terms])
        formatted_topics.append(f"Topic {topic_id}: [{terms_str}]")

    return "\n".join(formatted_topics)


def infer_topic_names(model: LdaModel, llm) -> dict:
    """
    Use LangChain + LLM to infer meaningful names for LDA topics.

    Args:
        model: Trained LDA model
        llm: LangChain LLM instance (e.g., ChatOllama, ChatOpenAI)

    Returns a dictionary with inferred topic names and rationales.
    """
    # Load prompt template
    if not Path(LDA_TOPICS).exists():
        raise FileNotFoundError(f"Prompt file not found at {LDA_TOPICS}")

    with open(str(LDA_TOPICS), 'r', encoding='utf-8') as f:
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

    print(f"Topic inference saved to {output_path}")


def main(llm=None):
    """
    Main pipeline: load LDA model, infer topic names, save results.

    Args:
        llm: LangChain LLM instance (default: llama3.1:8b via Ollama)
    """
    # Use default llama3.1:8b via Ollama if no LLM provided
    if llm is None:
        llm = ChatOllama(model="llama3.1:8b", temperature=0.3)
        print("Using default LLM: llama3.1:8b")

    # Load trained LDA model
    if not Path(TRAINED_LDA).exists():
        raise FileNotFoundError(
            f"Trained LDA model not found at {TRAINED_LDA}")

    print(f"Loading trained LDA model from {TRAINED_LDA}")
    model = LdaModel.load(str(TRAINED_LDA))
    print(f"Model loaded. Number of topics: {model.num_topics}")

    # Infer topic names via LLM
    inference_result = infer_topic_names(model, llm)

    # Save results
    save_topic_inference(inference_result.model_dump(), Path(TOPIC_INFERENCE))

    # Print summary
    print("\n=== Topic Inference Results ===")
    for topic in inference_result.topics:
        print(f"Topic {topic.topic_id}: {topic.inferred_name}")
        print(f"  Rationale: {topic.rationale}\n")


if __name__ == '__main__':
    main()
