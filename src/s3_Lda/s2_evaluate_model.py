import logging
from typing import Iterable, Tuple, List, Optional
import os
from pathlib import Path
import json
from gensim.corpora import MmCorpus
from paths import TRAINED_LDA, TRAINED_DCT, TRAINED_BOW

import gensim
from gensim.corpora.dictionary import Dictionary
from gensim.models.ldamodel import LdaModel
from gensim.models.coherencemodel import CoherenceModel
import logging as _logging
# silence noisy ldamodel warnings coming from gensim internals
_logging.getLogger('gensim.models.ldamodel').setLevel(_logging.ERROR)

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def make_dct_bow(corpora: Iterable[List[str]], no_below: int = 5, no_above: float = 0.5) -> Tuple[Dictionary, List[List[tuple]]]:
    """Create a gensim Dictionary and BOW corpus from tokenized texts.

    Returns (dictionary, bow_corpus)
    """
    dct = Dictionary(corpora)
    dct.filter_extremes(no_below=no_below, no_above=no_above)
    bow = [dct.doc2bow(doc) for doc in corpora]
    return dct, bow


def find_best_model(
    texts: Iterable[List[str]],
    dictionary: Dictionary,
    bow_corpus: List[List[tuple]],
    topic_range: Iterable[int] = range(2, 9),
    # avoid 'auto' values in grid search by default to reduce instability warnings
    alphas: Iterable = (0.1, 0.5, 1.0),
    etas: Iterable = (0.1, 0.5, 1.0),
    passes: int = 50,
    iterations: int = 100,
    coherence: str = 'c_v'
) -> Tuple[LdaModel, dict]:
    """Grid search for best LDA model based on coherence.

    Returns (best_model, best_config)
    """
    best_score = float('-inf')
    best_model = None
    best_config = None

    for num_topics in topic_range:
        logger.info(f"Testing num_topics={num_topics}")
        for alpha in alphas:
            for eta in etas:
                try:
                    model = LdaModel(
                        corpus=bow_corpus,
                        id2word=dictionary,
                        num_topics=num_topics,
                        alpha=alpha,
                        eta=eta,
                        passes=passes,
                        iterations=iterations,
                    )
                    cm = CoherenceModel(model=model, texts=list(
                        texts), dictionary=dictionary, coherence=coherence)
                    score = cm.get_coherence()
                    logger.info(
                        f"num_topics={num_topics} alpha={alpha} eta={eta} coherence={score:.4f}")
                    if score > best_score:
                        best_score = score
                        best_model = model
                        best_config = {"num_topics": num_topics,
                                       "alpha": alpha, "eta": eta, "coherence": score}
                except Exception as e:
                    logger.exception(
                        "Model training failed for configuration", exc_info=e)

    if best_model is None:
        raise RuntimeError("No model could be trained")

    return best_model, best_config


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
    """Create dictionary/bow and return a trained LDA model.

    If use_search is True, runs `find_best_model` grid search and returns the best model.
    Otherwise trains a default model using median topic count from topic_range.
    Returns (model, dictionary, bow_corpus, best_config)
    """
    dictionary, bow_corpus = make_dct_bow(
        list(texts), no_below=no_below, no_above=no_above)

    if use_search:
        model, best_config = find_best_model(
            texts,
            dictionary,
            bow_corpus,
            topic_range=topic_range,
            passes=max(10, passes // 2),
            iterations=max(50, iterations // 2),
        )
    else:
        # Use provided LDA params if given, otherwise derive sensible defaults
        if lda_num_topics is not None:
            num_topics = int(lda_num_topics)
        else:
            num_topics = int(sum(topic_range) / len(list(topic_range)))

        alpha = lda_alpha if lda_alpha is not None else (1.0 / num_topics)
        eta = lda_eta if lda_eta is not None else (1.0 / num_topics)

        model = LdaModel(
            corpus=bow_corpus,
            id2word=dictionary,
            num_topics=num_topics,
            alpha=alpha,
            eta=eta,
            passes=passes,
            iterations=iterations,
            random_state=random_state,
        )
        best_config = {"num_topics": num_topics, "alpha": alpha, "eta": eta}

    # After training, save model, dictionary and bow corpus so they can be reloaded later.
    try:
        # ensure directory exists
        lda_dir = Path(TRAINED_LDA).parent
        lda_dir.mkdir(parents=True, exist_ok=True)

        model.save(str(TRAINED_LDA))
        dictionary.save(str(TRAINED_DCT))
        # serialize bow corpus to Matrix Market format
        MmCorpus.serialize(str(TRAINED_BOW), bow_corpus)

        # Persist best_config as metadata next to model for quick inspection
        meta_path = str(Path(TRAINED_LDA).with_suffix('.meta.json'))
        with open(meta_path, 'w', encoding='utf-8') as mf:
            json.dump(best_config or {}, mf, indent=2)
    except Exception as e:
        logger.exception('Failed to save trained model artifacts', exc_info=e)

    return model, dictionary, bow_corpus, best_config
