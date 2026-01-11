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
    """
    Gera visualização interativa pyLDAvis e salva como HTML.
    
    Correções:
    - Usa preparação correta do modelo
    - Garante que o diretório existe antes de salvar
    - Fecha a figura matplotlib se necessário
    """
    try:
        lda = LdaModel.load(str(model_path / TRAINED_LDA))
        dictionary = Dictionary.load(str(model_path / TRAINED_DCT))
        corpus = MmCorpus(str(model_path / TRAINED_BOW))
        
        vis = gensimvisualize.prepare(lda, corpus, dictionary, mds='mmds', sort_topics=False)
        
        output_path = model_path / 'pyldavis.html'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        pyLDAvis.save_html(vis, str(output_path))
        print(f"✓ pyLDAvis salvo em: {output_path}")
        
    except Exception as e:
        print(f"✗ Erro ao gerar pyLDAvis para {model_path}: {e}")
        import traceback
        traceback.print_exc()

def stat_plots(model_path):
    """
    Gera gráficos estatísticos sobre a distribuição de tópicos.
    
    Correções:
    - Fecha figuras explicitamente para evitar warnings
    - Usa Path objects consistentemente
    - Adiciona tratamento de erros
    """
    try:
        df = pd.read_csv(CLASSIFIED_POSTS)   
        df['topic'] = df['topic'].apply(
            lambda x: x[:15] + '...' if type(x) == str and len(x) > 15 else x
        )
        
        Path(model_path).mkdir(parents=True, exist_ok=True)
        
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
        
        output_path_1 = Path(model_path) / 'prob_distribution.png'
        plt.savefig(output_path_1, dpi=300, bbox_inches='tight')
        plt.close() 
        print(f"✓ Gráfico de probabilidade salvo em: {output_path_1}")
        

        topic_counts = df['topic'].value_counts().sort_values(ascending=False)
        plt.figure(figsize=(10, len(topic_counts) * 0.4))
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
        
        output_path_2 = Path(model_path) / 'topic_distribution.png'
        plt.savefig(output_path_2, dpi=300, bbox_inches='tight')
        plt.close()  # IMPORTANTE: Fecha a figura
        print(f"✓ Gráfico de distribuição salvo em: {output_path_2}")
        
    except Exception as e:
        print(f"✗ Erro ao gerar gráficos estatísticos: {e}")
        import traceback
        traceback.print_exc()
        plt.close('all') 


if __name__ == '__main__':
    print("\n[1/16] Processando modelo principal...")
    main_path = MODELS / 'main'
    stat_plots(main_path)
    for c in range(15):
        print(f"\n[{c+2}/16] Processando modelo t{c}...")
        path = MODELS / f't{c}'
        stat_plots(path)

    
    print("\n" + "=" * 60)
    print("Processamento concluído!")
    print("=" * 60)