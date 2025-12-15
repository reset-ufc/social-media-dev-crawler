from pathlib import Path
import pandas as pd
from paths import CLASSIFIED_POSTS, LDA_DIR
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_topics_document(classified_path: str = CLASSIFIED_POSTS,
                             output_filename: str = 'topics_structure.txt') -> str:
    """
    Generate a text document with topics and subtopics hierarchically organized,
    sorted by percentage in descending order.

    Structure:
    Topic Name: XX% of total posts
     - Subtopic: YY% of posts in this topic
     - Subtopic: YY% of posts in this topic

    Topic Name: XX% of total posts
     - Subtopic: YY% of posts in this topic

    Args:
        classified_path: Path to CLASSIFIED_POSTS CSV file
        output_filename: Name of output text file to be saved in LDA_DIR

    Returns:
        Path to generated file
    """

    # Read data
    df = pd.read_csv(classified_path)

    # Filter only questions
    df = df[df['type'] == 'question'].copy()

    total_posts = len(df)

    # Calculate topic percentages (of total posts)
    topic_counts = df['topic'].value_counts()
    topic_percentages = (topic_counts / total_posts * 100).to_dict()

    # Sort topics by percentage (descending)
    sorted_topics = sorted(topic_percentages.items(),
                           key=lambda x: x[1], reverse=True)

    # Build document lines
    lines = []
    lines.append("=" * 80)
    lines.append("TOPICS AND SUBTOPICS HIERARCHY")
    lines.append("=" * 80)
    lines.append("")

    for topic, topic_pct in sorted_topics:
        # Add topic with percentage
        lines.append(
            f"{topic}: {topic_pct:.2f}% ({int(topic_counts[topic])} posts)")

        # Get all posts for this topic
        topic_posts = df[df['topic'] == topic]

        # Calculate subtopic percentages (of posts in this topic)
        subtopic_counts = topic_posts['subtopic'].value_counts()
        subtopic_percentages = (
            subtopic_counts / len(topic_posts) * 100).to_dict()

        # Sort subtopics by percentage (descending)
        sorted_subtopics = sorted(
            subtopic_percentages.items(), key=lambda x: x[1], reverse=True)

        # Add subtopics
        for subtopic, subtopic_pct in sorted_subtopics:
            subtopic_count = int(subtopic_counts[subtopic])
            lines.append(
                f"  - {subtopic}: {subtopic_pct:.2f}% ({subtopic_count} posts)")

        lines.append("")

    # Add summary section
    lines.append("")
    lines.append("=" * 80)
    lines.append("SUMMARY")
    lines.append("=" * 80)
    lines.append(f"Total posts: {total_posts}")
    lines.append(f"Total topics: {len(sorted_topics)}")
    total_subtopics = df['subtopic'].nunique()
    lines.append(f"Total unique subtopics: {total_subtopics}")

    # Write to file
    output_path = Path(LDA_DIR) / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Document generated: {output_path}")
    print(f"Total lines: {len(lines)}")

    return str(output_path)


if __name__ == '__main__':
    generate_topics_document()
