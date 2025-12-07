import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gensim.corpora import MmCorpus
from gensim.corpora.dictionary import Dictionary
from gensim.models.ldamodel import LdaModel
import pyLDAvis
import pyLDAvis.gensim_models as gensimvisualize
import pandas as pd 
import seaborn as sns
import matplotlib.pyplot as plt

from paths import *


def pldavis(model_path): 
    try:
        lda = LdaModel.load(str(model_path / TRAINED_LDA))
        dictionary = Dictionary.load(str(model_path / TRAINED_DCT))
        corpus = MmCorpus(str(model_path / TRAINED_BOW))

        # corpus may be an iterable of (id, count) pairs or an MmCorpus object; pyLDAvis accepts both
        vis = gensimvisualize.prepare(lda, corpus, dictionary, mds='mmds')
    except Exception as e:
        print(e)
    Path(model_path / 'pyldavis.html').parent.mkdir(parents=True, exist_ok=True)
    pyLDAvis.save_html(vis, str(model_path / 'pyldavis.html'))


def stat_plots(model_path):
    df = pd.read_csv(CLASSIFIED_POSTS)   
    df['topic'] = df['topic'].apply(
    lambda x: x[:15] + '...' if type(x) == str and len(x) > 15 else x)

    plt.figure(figsize=(15, 7))
    sns.boxplot(
        x='topic',         
        y='topic_perc_contrib', 
        data=df,
        palette='viridis'       
    )
    plt.title('Probability Distribution', fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=9) 
    plt.tight_layout()
    plt.savefig(model_path / 'prob_distribution.png', dpi=300)

    topic_counts = df['topic'].value_counts().sort_values(ascending=False)
    plt.figure(figsize=(10, len(topic_counts) * 0.4)) # Ajusta a altura da figura dinamicamente
    sns.barplot(
        x=topic_counts.values,   
        y=topic_counts.index,    
        palette='Spectral' 
    )
    plt.title('Distribution of documents per topic', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Number of documents', fontsize=12)
    plt.ylabel('Topic', fontsize=12)
    sns.despine(trim=True, top=True, right=True)
    for index, value in enumerate(topic_counts.values):
        plt.text(value, index, f' {value}', va='center')
    plt.tight_layout()
    plt.savefig(model_path / 'topic_distribution.png', dpi=300)


def words_per_topic(model_path, num_words: int = 20) -> str:
    model = LdaModel.load(str(model_path / TRAINED_LDA))
    formatted_topics = []
    for topic_id in range(model.num_topics):
        top_terms = model.show_topic(topic_id, topn=num_words)
        top_terms = sorted(top_terms, key=lambda x: x[1], reverse=True)
        terms_str = ", ".join(
            [f'word: "{word}" weight: ({weight:.3f})' for word, weight in top_terms])
        formatted_topics.append(f"Topic {topic_id}: [{terms_str}]")
    with open(model_path / f'topics.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(formatted_topics))


if __name__ == '__main__':
    path = MODELS / 'main1'
    pldavis(path)
    stat_plots(path)
    words_per_topic(path)
    