import multiprocessing
from paths import NORMALIZED_POSTS, TRAINED_LDA, TRAINED_DCT, TRAINED_BOW, LDA_VISUALIZATION
from s3_infer_topics import main as infer_topics
from s3_Lda import s1_normalisation
from s3_Lda import s2_evaluate_model
import pandas as pd
import pyLDAvis.gensim_models as gensimvisualize
import pyLDAvis
from gensim.models.ldamodel import LdaModel
from gensim.corpora.dictionary import Dictionary
from gensim.corpora import MmCorpus
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_pipeline(use_search: bool = True, llm=None, num_topics: int = None, alpha: float = None, eta: float = None):

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
        texts,
        use_search=use_search,
        lda_num_topics=num_topics,
        lda_alpha=alpha,
        lda_eta=eta,
    )
    print('Model trained. Config:', cfg)

    # 4) Prepare visualization
    print('Preparing visualization...')
    # Prefer using in-memory artifacts returned by evaluate_model to ensure indices align
    try:
        if 'model' in locals() and 'dct' in locals() and 'bow' in locals() and model is not None:
            lda = model
            dictionary = dct
            corpus = bow
        else:
            lda = LdaModel.load(str(TRAINED_LDA))
            dictionary = Dictionary.load(str(TRAINED_DCT))
            corpus = MmCorpus(str(TRAINED_BOW))

        # corpus may be an iterable of (id, count) pairs or an MmCorpus object; pyLDAvis accepts both
        vis = gensimvisualize.prepare(lda, corpus, dictionary, mds='mmds')
    except Exception as e:
        print(e)
    Path(LDA_VISUALIZATION).parent.mkdir(parents=True, exist_ok=True)
    pyLDAvis.save_html(vis, str(LDA_VISUALIZATION))
    print(f'Visualization saved to {LDA_VISUALIZATION}')

    # call topic inference, passing the chosen LLM if provided
    try:
        infer_topics(llm)
    except TypeError:
        # fallback if infer_topics expects no args (backward compatibility)
        infer_topics()


if __name__ == '__main__':
    # Ensure safe multiprocessing start method to avoid fork-related DeprecationWarnings
    try:
        current = multiprocessing.get_start_method()
    except RuntimeError:
        current = None

    if current != 'spawn':
        try:
            multiprocessing.set_start_method("spawn", force=True)
        except RuntimeError:
            # already set by child process; ignore
            pass

    run_pipeline()
