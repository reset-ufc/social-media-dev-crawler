import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
from typing import Iterable, Tuple, List, Optional
import os
from pathlib import Path
import json
from gensim.corpora import MmCorpus
from paths import *

import gensim
from gensim.corpora.dictionary import Dictionary
from gensim.models.ldamodel import LdaModel
from gensim.models.wrappers import LdaMallet
from gensim.models.wrappers.ldamallet import malletmodel2ldamodel
from gensim.models.coherencemodel import CoherenceModel
import logging as _logging
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# silence noisy ldamodel warnings coming from gensim internals
_logging.getLogger('gensim.models.ldamodel').setLevel(_logging.ERROR)

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ----------------------------------------------------------------------
#   CREATE DICTIONARY + BOW
# ----------------------------------------------------------------------
def make_dct_bow(corpora: Iterable[List[str]], no_below: int = 5, no_above: float = 0.5) -> Tuple[Dictionary, List[List[tuple]]]:
    dct = Dictionary(corpora)
    dct.filter_extremes(no_below=no_below, no_above=no_above)
    bow = [dct.doc2bow(doc) for doc in corpora]
    return dct, bow


# ----------------------------------------------------------------------
#   GRID SEARCH USING MALLET
# ----------------------------------------------------------------------
def find_best_model(
    texts: Iterable[List[str]],
    dictionary: Dictionary,
    bow_corpus: List[List[tuple]],
    topic_range: Iterable[int] = range(2, 9),
    iterations: int = 100,
    coherence: str = 'c_v'
) -> Tuple[LdaModel, dict]:

    mallet_home = os.environ.get("MALLET_HOME", "/opt/mallet")
    mallet_path = os.path.join(mallet_home, "bin", "mallet")

    if not os.path.exists(mallet_path):
        raise RuntimeError(f"Mallet binary not found at {mallet_path}")

    best_score = float('-inf')
    best_model = None
    best_config = None

    for num_topics in topic_range:
        logger.info(f"Testing num_topics={num_topics}")
        alpha = num_topics / 50.0

        try:
            mallet_model = LdaMallet(
                mallet_path=mallet_path,
                corpus=bow_corpus,
                id2word=dictionary,
                num_topics=num_topics,
                alpha=alpha,
                iterations=iterations,
            )

            # convert MALLET → Gensim LdaModel (correct!)
            model = malletmodel2ldamodel(mallet_model)

            cm = CoherenceModel(model=model, texts=list(texts), dictionary=dictionary, coherence=coherence)
            score = cm.get_coherence()

            logger.info(f"num_topics={num_topics} | alpha={alpha} | coherence={score:.4f}")

            if score > best_score:
                best_score = score
                best_model = model
                best_config = {"num_topics": num_topics, "alpha": alpha, "coherence": score}

        except Exception as e:
            logger.exception("Model training failed for configuration", exc_info=e)

    if best_model is None:
        raise RuntimeError("No model could be trained")

    return best_model, best_config


# ----------------------------------------------------------------------
#   MAIN TRAINING FUNCTION
# ----------------------------------------------------------------------
def evaluate_model(
    texts: Iterable[List[str]],
    no_below: int = 5,
    no_above: float = 0.5,
    topic_range: Iterable[int] = range(2, 9),
    use_search: bool = True,
    passes: int = 100,
    iterations: int = 150,
    random_state: Optional[int] = None,
    lda_num_topics: Optional[int] = None,
    lda_alpha: Optional[float] = None,
    lda_eta: Optional[float] = None,
):
    # resolve MALLET
    mallet_home = os.environ.get('MALLET_HOME', r'C:\mallet')
    mallet_path = os.path.join(mallet_home, "bin", "mallet")

    if not os.path.exists(mallet_path):
        raise RuntimeError(f"Mallet binary not found at: {mallet_path}")

    texts = list(texts)

    dictionary, bow_corpus = make_dct_bow(texts, no_below=no_below, no_above=no_above)

    logger.info(f"Dictionary size: {len(dictionary)}")
    logger.info(f"Example BOW doc: {bow_corpus[0] if bow_corpus else 'EMPTY BOW'}")

    topic_range = list(topic_range)

    if use_search:
        model, best_config = find_best_model(
            texts,
            dictionary,
            bow_corpus,
            topic_range=topic_range,
            iterations=max(50, iterations // 2),
        )

    else:
        num_topics = int(lda_num_topics or (sum(topic_range) / len(topic_range)))
        alpha = lda_alpha if lda_alpha is not None else (50 / num_topics)

        mallet_model = LdaMallet(
            mallet_path=mallet_path,
            corpus=bow_corpus,
            id2word=dictionary,
            num_topics=num_topics,
            alpha=alpha,
            iterations=iterations,
        )

        # convert ALWAYS
        model = malletmodel2ldamodel(mallet_model)

        best_config = {"num_topics": num_topics, "alpha": alpha}

    # ------------------------------------------------------------------
    # SAVE ARTIFACTS — FIXED (consistent formats, no more errors)
    # ------------------------------------------------------------------
    try:
        lda_dir = Path(TRAINED_LDA).parent
        lda_dir.mkdir(parents=True, exist_ok=True)

        # save Gensim LdaModel (correct!)
        model.save(str(TRAINED_LDA))

        dictionary.save(str(TRAINED_DCT))
        MmCorpus.serialize(str(TRAINED_BOW), bow_corpus)

        meta_path = str(Path(TRAINED_LDA).with_suffix(".meta.json"))
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(best_config, mf, indent=2)

        logger.info("✔ Model saved successfully")

    except Exception as e:
        logger.exception("Failed to save trained model artifacts", exc_info=e)


# ----------------------------------------------------------------------
#   RUN TRAINING
# ----------------------------------------------------------------------
if __name__ == '__main__':
    df = pd.read_csv(str(NORMALIZED_POSTS))

    if 'normalized_text' in df.columns:
        texts = df['normalized_text'].fillna('').map(lambda s: s.split()).tolist()

    elif 'normalized' in df.columns:
        # support for lists stored as strings
        texts = df['normalized'].fillna('').map(
            lambda s: eval(s) if isinstance(s, str) and s.startswith('[')
            else str(s).split()
        ).tolist()

    else:
        raise RuntimeError("No normalized_text or normalized column found in CSV")

    evaluate_model(texts)
