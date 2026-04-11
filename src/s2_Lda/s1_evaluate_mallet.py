import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
import subprocess
from dotenv import load_dotenv
import pandas as pd
import logging as _logging
from gensim.models.coherencemodel import CoherenceModel
from gensim.models.wrappers.ldamallet import malletmodel2ldamodel
from gensim.models.wrappers import LdaMallet
from gensim.models.ldamodel import LdaModel
from gensim.corpora.dictionary import Dictionary
from paths import *
from gensim.corpora import MmCorpus
import json
from pathlib import Path
from typing import Iterable, Tuple, List, Optional
import logging


load_dotenv()

# silence noisy ldamodel warnings coming from gensim internals
_logging.getLogger('gensim.models.ldamodel').setLevel(_logging.ERROR)

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Default values in gensim
DEFAULT_NO_BELOW = 5
DEFAULT_NO_ABOVE = 0.5

DEFAULT_TOPIC_RANGE = range(1, 25+1)
DEFAULT_ITERATIONS = 2000
DEFAULT_COHERENCE = 'c_v'
DEFAULT_RANDOM_STATE = 7562
DEFAULT_LDA_BETA = 0.01
DEFAULT_WORKERS = 4


def _default_mallet_home():
    """Return a sensible default for MALLET_HOME depending on OS or environment."""
    env = os.environ.get('MALLET_HOME')
    if env:
        return env
    return r'C:\mallet' if os.name == 'nt' else '/opt/mallet'


def calculate_perplexity_from_mallet(model, bow_corpus):
    """
    Calculate perplexity using topic-document distributions from Mallet.
    This approach is more robust for models converted from Mallet.
    """
    try:
        # Get topic-document distributions
        doc_topics = [model.get_document_topics(
            doc, minimum_probability=0) for doc in bow_corpus]

        total_log_likelihood = 0
        total_words = 0

        for doc_idx, doc in enumerate(bow_corpus):
            doc_topic_dist = dict(doc_topics[doc_idx])

            for word_id, word_count in doc:
                word_prob = 0
                for topic_id in range(model.num_topics):
                    topic_prob = doc_topic_dist.get(topic_id, 0)
                    word_given_topic = model.expElogbeta[topic_id][word_id]
                    word_prob += topic_prob * word_given_topic

                if word_prob > 0:
                    total_log_likelihood += word_count * np.log(word_prob)
                    total_words += word_count

        if total_words == 0:
            return float('nan')

        perplexity = np.exp(-total_log_likelihood / total_words)
        return float(perplexity)

    except Exception as e:
        logger.warning(f"Failed to calculate perplexity: {e}")
        return float('nan')


def calculate_perplexity_alternative(model, bow_corpus):
    """
    Alternative method using bound() directly.
    Faster but may be less accurate for converted Mallet models.
    """
    try:
        per_word_bound = model.bound(
            bow_corpus) / sum(cnt for doc in bow_corpus for _, cnt in doc)
        perplexity = np.exp2(-per_word_bound)
        return float(perplexity)
    except Exception as e:
        logger.warning(f"Alternative perplexity calculation failed: {e}")
        return float('nan')


def words_per_topic(model_path, num_words: int = 20) -> str:
    """
    Extract and save the most important words from each topic.

    Args:
        model_path: Path to the model directory
        num_words: Number of words per topic (default: 20)

    Returns:
        Path to the saved file or None in case of error
    """
    try:
        model = LdaModel.load(str(model_path / TRAINED_LDA))
        formatted_topics = []

        for topic_id in range(model.num_topics):
            top_terms = model.show_topic(topic_id, topn=num_words)
            top_terms = sorted(top_terms, key=lambda x: x[1], reverse=True)
            terms_str = ", ".join(
                [f'word: "{word}" weight: ({weight:.3f})' for word,
                 weight in top_terms]
            )
            formatted_topics.append(f"Topic {topic_id}: [{terms_str}]")

        Path(model_path).mkdir(parents=True, exist_ok=True)

        output_path = Path(model_path) / 'topics.txt'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(formatted_topics))

        logger.info(f"Topics saved to: {output_path}")
        return str(output_path)

    except Exception as e:
        logger.exception(f"Failed to extract topic words: {e}")
        return None


def train_mallet_with_beta(
    mallet_path,
    corpus,
    id2word,
    num_topics,
    alpha,
    beta,
    iterations,
    random_seed,
    workers=DEFAULT_WORKERS,
    prefix=None
):
    """
    Train Mallet LDA model with support for beta parameter.
    Returns a trained LdaMallet object.
    """
    # Create basic instance without training
    model = LdaMallet(
        mallet_path=mallet_path,
        corpus=None,
        num_topics=num_topics,
        alpha=alpha,
        id2word=id2word,
        workers=workers,
        prefix=prefix,
        iterations=iterations,
        random_seed=random_seed
    )

    # Convert corpus to Mallet format
    model.convert_input(corpus, infer=False)

    cmd = [
        model.mallet_path,
        'train-topics',
        '--input', model.fcorpusmallet(),
        '--num-topics', str(model.num_topics),
        '--alpha', str(alpha),
        '--beta', str(beta),
        '--optimize-interval', str(model.optimize_interval),
        '--num-threads', str(model.workers),
        '--output-state', model.fstate(),
        '--output-doc-topics', model.fdoctopics(),
        '--output-topic-keys', model.ftopickeys(),
        '--num-iterations', str(model.iterations),
        '--doc-topics-threshold', str(model.topic_threshold),
        '--random-seed', str(random_seed)
    ]

    logger.info(
        f"Training MALLET LDA: topics={num_topics}, alpha={alpha}, beta={beta}, seed={random_seed}")

    # Execute training
    subprocess.check_call(cmd)

    # Load word-topics
    model.word_topics = model.load_word_topics()
    model.wordtopics = model.word_topics

    return model


def make_dct_bow(corpora: Iterable[List[str]], no_below: int = 5, no_above: float = 0.5) -> Tuple[Dictionary, List[List[tuple]]]:
    dct = Dictionary(corpora)
    dct.filter_extremes(no_below=no_below, no_above=no_above)
    bow = [dct.doc2bow(doc) for doc in corpora]
    return dct, bow


def find_best_model(
    texts: Iterable[List[str]],
    dictionary: Dictionary,
    bow_corpus: List[List[tuple]],
    model_path,
    topic_range: Iterable[int] = DEFAULT_TOPIC_RANGE,
    iterations: int = DEFAULT_ITERATIONS,
    coherence: str = DEFAULT_COHERENCE,
    beta: float = DEFAULT_LDA_BETA,
    random_seed: int = DEFAULT_RANDOM_STATE
) -> Tuple[LdaModel, dict]:

    mallet_home = _default_mallet_home()
    mallet_path = os.path.join(mallet_home, "bin", "mallet")

    if not os.path.exists(mallet_path):
        raise RuntimeError(f"Mallet binary not found at {mallet_path}")

    best_score = float('-inf')
    best_model = None
    best_config = None

    topic_range = list(topic_range)
    scores = []
    perplexities = []

    for num_topics in topic_range:
        logger.info(f"Testing num_topics={num_topics}")
        alpha = 50.0 / num_topics  # Fixed formula

        try:
            mallet_model = train_mallet_with_beta(
                mallet_path=mallet_path,
                corpus=bow_corpus,
                id2word=dictionary,
                num_topics=num_topics,
                alpha=alpha,
                beta=beta,
                iterations=iterations,
                random_seed=random_seed
            )

            model = malletmodel2ldamodel(mallet_model)

            cm = CoherenceModel(model=model, texts=list(
                texts), dictionary=dictionary, coherence=coherence)
            score = cm.get_coherence()
            scores.append(score)

            perp = calculate_perplexity_from_mallet(model, bow_corpus)
            if np.isnan(perp):
                perp = calculate_perplexity_alternative(model, bow_corpus)

            perplexities.append(perp)

            logger.info(
                f"num_topics={num_topics} | alpha={alpha:.4f} | beta={beta} | seed={random_seed} | coherence={score:.4f} | perplexity={perp:.4f}")

            if score > best_score:
                best_score = score
                best_model = model
                best_config = {
                    "num_topics": num_topics,
                    "alpha": alpha,
                    "beta": beta,
                    "random_seed": random_seed,
                    "coherence": score,
                    "perplexity": perp
                }

        except Exception as e:
            logger.exception(
                "Model training failed for configuration", exc_info=e)
            perplexities.append(float('nan'))

    if best_model is None:
        raise RuntimeError("No model could be trained")
    else:
        # Coherence plot
        plt.figure(figsize=(10, 6))
        plt.plot(topic_range, scores, marker='o', linestyle='-', color='blue')
        plt.title('Coherence Score (C_V) by Number of Topics')
        plt.xlabel('Number of Topics (K)')
        plt.ylabel(f'Coherence Score ({coherence})')
        plt.xticks(topic_range)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.savefig(str(model_path/'coherence_plot.png'))

        # Perplexity plot
        valid_perplexities = [(k, p) for k, p in zip(
            topic_range, perplexities) if not np.isnan(p)]
        if valid_perplexities:
            valid_k, valid_p = zip(*valid_perplexities)
            plt.figure(figsize=(10, 6))
            plt.plot(valid_k, valid_p, marker='o',
                     linestyle='-', color='green')
            plt.title('Perplexity by Number of Topics')
            plt.xlabel('Number of Topics (K)')
            plt.ylabel('Perplexity')
            plt.xticks(topic_range)
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.savefig(str(model_path/'perplexity_plot.png'))
        else:
            logger.warning("No valid perplexity values to plot")

    return best_model, best_config


def evaluate_model(
    texts: Iterable[List[str]],
    model_path: Path,
    no_below: int = DEFAULT_NO_BELOW,
    no_above: float = DEFAULT_NO_ABOVE,
    topic_range: Iterable[int] = DEFAULT_TOPIC_RANGE,
    use_search: bool = True,
    iterations: int = DEFAULT_ITERATIONS,
    random_state: int = DEFAULT_RANDOM_STATE,
    lda_num_topics: Optional[int] = None,
    lda_beta: Optional[float] = DEFAULT_LDA_BETA,
    coherence: str = DEFAULT_COHERENCE,
):

    mallet_home = _default_mallet_home()
    mallet_path = os.path.join(mallet_home, "bin", "mallet")

    model_path.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(mallet_path):
        raise RuntimeError(f"Mallet binary not found at: {mallet_path}")

    texts = list(texts)

    dictionary, bow_corpus = make_dct_bow(
        texts, no_below=no_below, no_above=no_above)

    logger.info(f"Dictionary size: {len(dictionary)}")
    logger.info(
        f"Example BOW doc: {bow_corpus[0] if bow_corpus else 'EMPTY BOW'}")

    topic_range = list(topic_range)

    if use_search:
        model, best_config = find_best_model(
            texts,
            dictionary,
            bow_corpus,
            model_path=model_path,
            topic_range=topic_range,
            iterations=iterations,
            beta=lda_beta,
            random_seed=random_state
        )

    else:
        num_topics = int(lda_num_topics or (
            sum(topic_range) / len(topic_range)))
        alpha = 50.0 / num_topics  # Fixed formula

        mallet_model = train_mallet_with_beta(
            mallet_path=mallet_path,
            corpus=bow_corpus,
            id2word=dictionary,
            num_topics=num_topics,
            alpha=alpha,
            beta=lda_beta,
            iterations=iterations,
            random_seed=random_state
        )

        model = malletmodel2ldamodel(mallet_model)

        perp = calculate_perplexity_from_mallet(model, bow_corpus)
        if np.isnan(perp):
            perp = calculate_perplexity_alternative(model, bow_corpus)

        best_config = {
            "num_topics": num_topics,
            "alpha": alpha,
            "beta": lda_beta,
            "random_seed": random_state,
            "perplexity": perp
        }

    # SAVE ARTIFACTS
    try:
        model.save(str(model_path/TRAINED_LDA))

        dictionary.save(str(model_path/TRAINED_DCT))
        MmCorpus.serialize(str(model_path/TRAINED_BOW), bow_corpus)

        meta_path = str(Path(model_path/TRAINED_LDA).with_suffix(".meta.json"))
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(best_config, mf, indent=2)

        logger.info("Model saved successfully")
        logger.info(f"Best configuration: {best_config}")

        # Extract and save the most important words from each topic
        topics_file = words_per_topic(model_path, num_words=20)
        if topics_file:
            logger.info(f"Topic words saved to: {topics_file}")

    except Exception as e:
        logger.exception("Failed to save trained model artifacts", exc_info=e)


def run(name: str, main_topic: str = None, mode: str = None):
    if mode is None:
        mode = os.environ.get('LDA_MODE', 'search')

    if main_topic:
        df = pd.read_csv(str(CLASSIFIED_POSTS))
        qids = df[df['topic'] == main_topic]['question_id']
        df = df[df['question_id'].isin(qids)]
    else:
        df = pd.read_csv(str(NORMALIZED_POSTS))

    if 'normalized_text' in df.columns:
        texts = df['normalized_text'].fillna(
            '').map(lambda s: s.split()).tolist()
    elif 'normalized' in df.columns:
        # support for lists stored as strings
        texts = df['normalized'].fillna('').map(
            lambda s: eval(s) if isinstance(s, str) and s.startswith('[')
            else str(s).split()
        ).tolist()
    else:
        raise RuntimeError(
            "No normalized_text or normalized column found in CSV")

    return evaluate_model(
        texts,
        MODELS / name,
        lda_beta=0.01,
        use_search=(mode == 'search'),
        topic_range=DEFAULT_TOPIC_RANGE
    )


def run_submodels(main_path):
    kd = pd.read_json(
        Path(main_path / 'trained_lda.meta.json'), orient='index').T
    ti = pd.read_json(main_path / 'topic_inference.json')

    k = kd['num_topics'].item()
    for c in range(int(k)):
        topic = ti.loc[c]['topics']['topic_name']
        run(f't{c}', main_topic=topic)


if __name__ == '__main__':
    run('main')
    # run_submodels(MODELS / 'main')
