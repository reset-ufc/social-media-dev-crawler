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
from s3_Lda import s2_evaluate_model
from s3_Lda import s1_normalisation
from paths import NORMALIZED_POSTS, TRAINED_LDA, TRAINED_DCT, TRAINED_BOW, LDA_VISUALIZATION



def run_pipeline(use_search: bool = True):
    # 1) Normalize posts -> produces NORMALIZED_POSTS
    print('Running normalization...')
    try:
        s1_normalisation.main()
    except Exception as e:
        print('Normalization failed:', e)
        raise

    if not Path(NORMALIZED_POSTS).exists():
        raise FileNotFoundError(
            f'Normalized posts not found at {NORMALIZED_POSTS}')

    # 2) Load normalized posts and prepare texts
    df = pd.read_csv(str(NORMALIZED_POSTS))
    if 'normalized_text' not in df.columns:
        # fallback: if normalized column exists as list-like in CSV, try to read
        if 'normalized' in df.columns:
            texts = df['normalized'].fillna('').map(lambda s: eval(s) if isinstance(
                s, str) and s.startswith('[') else str(s).split()).tolist()
        else:
            raise RuntimeError(
                'No normalized_text or normalized column found in normalized posts')
    else:
        texts = df['normalized_text'].fillna(
            '').map(lambda s: s.split()).tolist()

    # 3) Train/evaluate model (this function also saves artifacts)
    print('Training/evaluating LDA model...')
    model, dct, bow, cfg = s2_evaluate_model.evaluate_model(
        texts, use_search=use_search)
    print('Model trained. Config:', cfg)

    # 4) Load saved artifacts to prepare visualization (use saved files to ensure reproducible pipeline)
    print('Preparing visualization...')
    lda = LdaModel.load(str(TRAINED_LDA))
    dictionary = Dictionary.load(str(TRAINED_DCT))
    corpus = MmCorpus(str(TRAINED_BOW))

    vis = gensimvisualize.prepare(lda, corpus, dictionary, mds='mmds')
    Path(LDA_VISUALIZATION).parent.mkdir(parents=True, exist_ok=True)
    pyLDAvis.save_html(vis, str(LDA_VISUALIZATION))
    print(f'Visualization saved to {LDA_VISUALIZATION}')


if __name__ == '__main__':
    run_pipeline()
