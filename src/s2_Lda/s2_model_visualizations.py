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


def pldavis(model_path: Path): 
    try:
        lda = LdaModel.load(str(model_path / TRAINED_LDA))
        dictionary = Dictionary.load(str(model_path / TRAINED_DCT))
        corpus = MmCorpus(str(model_path / TRAINED_BOW))

        # corpus may be an iterable of (id, count) pairs or an MmCorpus object; pyLDAvis accepts both
        vis = gensimvisualize.prepare(lda, corpus, dictionary, mds='mmds')
        pyLDAvis.save_html(vis, str(model_path/ 'pyLDAvis.html'))
    except Exception as e:
        print(e)
    


def stat_plots(model_path: Path):
    df = pd.read_csv(CLASSIFIED_POSTS)   
    df['topic'] = df['topic'].apply(
    lambda x: x[:15] + '...' if type(x) == str and len(x) > 15 else x)

    plt.figure(figsize=(15, 7))
    sns.boxplot(
        x='topic',          # <-- Usando o novo rótulo curto
        y='topic_perc_contrib', 
        data=df,
        palette='viridis'       
    )
    plt.title('Probability Distribution', fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=9) 
    plt.tight_layout()
    plt.savefig(str(model_path / 'prob_dist.png'))


    topic_counts = df['topic'].value_counts().sort_values(ascending=False)
    plt.figure(figsize=(10, len(topic_counts) * 0.4)) # Ajusta a altura da figura dinamicamente
    sns.barplot(
        x=topic_counts.values,   # Os valores (Count) no eixo X
        y=topic_counts.index,    # Os rótulos (Topics) no eixo Y
        palette='Spectral'       # Escolhe uma paleta de cores atraente (ex: 'Spectral', 'viridis', 'pastel')
    )
    plt.title('Distribution of documents per topic', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Number of documents', fontsize=12)
    plt.ylabel('Topic', fontsize=12)
    sns.despine(trim=True, top=True, right=True)
    for index, value in enumerate(topic_counts.values):
        plt.text(value, index, f' {value}', va='center') # Adiciona o número ao lado da barra

    plt.tight_layout()
    plt.savefig(str(model_path / 'topics_dist.png'))


if __name__ == '__main__':
    path = MODELS / 'main'
    pldavis(path)
    stat_plots(path)
