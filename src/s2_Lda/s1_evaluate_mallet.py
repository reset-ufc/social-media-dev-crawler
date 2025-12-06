import logging
from typing import Iterable, Tuple, List, Optional
from pathlib import Path
import json
from gensim.corpora import MmCorpus
from paths import *
from gensim.corpora.dictionary import Dictionary
from gensim.models.ldamodel import LdaModel
from gensim.models.wrappers import LdaMallet
from gensim.models.wrappers.ldamallet import malletmodel2ldamodel
from gensim.models.coherencemodel import CoherenceModel
import logging as _logging
import pandas as pd
from dotenv import load_dotenv
import subprocess
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


load_dotenv()

# silence noisy ldamodel warnings coming from gensim internals
_logging.getLogger('gensim.models.ldamodel').setLevel(_logging.ERROR)

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ============ DEFAULT CONFIGURATION CONSTANTS ============
DEFAULT_NO_BELOW = 5
DEFAULT_NO_ABOVE = 0.5
DEFAULT_TOPIC_RANGE = range(1, 50)
DEFAULT_ITERATIONS = 2000
DEFAULT_COHERENCE = 'c_v'
DEFAULT_RANDOM_STATE = 7562
DEFAULT_LDA_BETA = 0.01
DEFAULT_WORKERS = 4

# Tuning grid search parameters
TUNING_ALPHAS = [0.001, 0.01, 0.1, 0.5, 1]
TUNING_BETAS = [0.001, 0.01, 0.1, 0.5, 1]
# =========================================================


def _default_mallet_home():
    """Return a sensible default for MALLET_HOME depending on OS or environment."""
    env = os.environ.get('MALLET_HOME')
    if env:
        return env
    return r'C:\mallet' if os.name == 'nt' else '/opt/mallet'


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
    Treina modelo LDA Mallet com suporte ao parâmetro beta
    Retorna um objeto LdaMallet treinado
    """
    # Criar instância básica sem treinar
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

    # Converter corpus para formato Mallet
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

    # Executar treinamento
    subprocess.check_call(cmd)

    # Carregar word-topics
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
        alpha = num_topics / 50.0

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

            # compute perplexity (per-word bound -> perplexity)
            try:
                per_word_bound = model.log_perplexity(bow_corpus)
                perp = float(np.exp(-per_word_bound))
            except Exception:
                perp = float('nan')
            perplexities.append(perp)

            logger.info(
                f"num_topics={num_topics} | alpha={alpha} | beta={beta} | seed={random_seed} | coherence={score:.4f}")

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
            # keep alignment for plotting when training fails
            perplexities.append(float('nan'))

    if best_model is None:
        raise RuntimeError("No model could be trained")
    else:
        # Coherence plot
        plt.figure(figsize=(10, 6))
        plt.plot(topic_range, scores, marker='o', linestyle='-', color='blue')
        plt.title('Score de Coerência (C_V) por Número de Tópicos')
        plt.xlabel('Número de Tópicos (K)')
        plt.ylabel(f'Score de Coerência ({coherence})')
        plt.xticks(topic_range)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.savefig(str(model_path/'coherence_plot.png'))

        plt.figure(figsize=(10, 6))
        plt.plot(topic_range, perplexities, marker='o',
                    linestyle='-', color='green')
        plt.title('Perplexity por Número de Tópicos')
        plt.xlabel('Número de Tópicos (K)')
        plt.ylabel('Perplexity')
        plt.xticks(topic_range)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.savefig(str(model_path/'perplexity_plot.png'))


    return best_model, best_config


def evaluate_model(
    texts: Iterable[List[str]],
    model_path: Path,
    no_below: int = DEFAULT_NO_BELOW,
    no_above: float = DEFAULT_NO_ABOVE,
    topic_range: Iterable[int] = DEFAULT_TOPIC_RANGE,
    use_search: bool = True,
    tuning: bool = False,
    iterations: int = DEFAULT_ITERATIONS,
    random_state: int = DEFAULT_RANDOM_STATE,
    lda_num_topics: Optional[int] = None,
    lda_alpha: Optional[float] = None,
    lda_beta: Optional[float] = DEFAULT_LDA_BETA,
    coherence: str = DEFAULT_COHERENCE,
):
    # resolve MALLET
    mallet_home = _default_mallet_home()
    mallet_path = os.path.join(mallet_home, "bin", "mallet")

    # Start model folder
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

    # If tuning requested, use the grid-search tuner function and return early
    if tuning:
        model, best_config = find_best_model_tunning(
            texts=texts,
            model_path=model_path,
            no_below=no_below,
            no_above=no_above,
            topic_range=topic_range,
            iterations=iterations,
            coherence=coherence,
            random_state=random_state,
        )

        return model, best_config

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
        alpha = lda_alpha if lda_alpha is not None else (50 / num_topics)

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

        # convert ALWAYS
        model = malletmodel2ldamodel(mallet_model)
        # compute perplexity for the single trained model
        try:
            per_word_bound = model.log_perplexity(bow_corpus)
            perp = float(np.exp(-per_word_bound))
        except Exception:
            perp = float('nan')

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

    except Exception as e:
        logger.exception("Failed to save trained model artifacts", exc_info=e)


def find_best_model_tunning(
    texts: Iterable[List[str]],
    model_path: Path,
    no_below: int = DEFAULT_NO_BELOW,
    no_above: float = DEFAULT_NO_ABOVE,
    topic_range: Iterable[int] = DEFAULT_TOPIC_RANGE,
    iterations: int = DEFAULT_ITERATIONS,
    coherence: str = DEFAULT_COHERENCE,
    random_state: int = DEFAULT_RANDOM_STATE,
    **kwargs
):
    """Grid search over alpha and beta for multiple K (topics).

    alpha and beta take values in [0.001, 0.01, 0.1, 0.5, 1].
    Does not plot results; returns best (model, config).
    """
    alphas = TUNING_ALPHAS
    betas = TUNING_BETAS
    tuning_records = []

    model_path.mkdir(parents=True, exist_ok=True)

    texts = list(texts)

    dictionary, bow_corpus = make_dct_bow(
        texts, no_below=no_below, no_above=no_above)

    best_score = float('-inf')
    best_model = None
    best_config = None

    for num_topics in topic_range:
        alpha_default = num_topics / 50.0
        for alpha in alphas:
            for beta in betas:
                try:
                    mallet_home = _default_mallet_home()
                    mallet_path = os.path.join(mallet_home, "bin", "mallet")
                    if not os.path.exists(mallet_path):
                        raise RuntimeError(
                            f"Mallet binary not found at {mallet_path}")

                    mallet_model = train_mallet_with_beta(
                        mallet_path=mallet_path,
                        corpus=bow_corpus,
                        id2word=dictionary,
                        num_topics=num_topics,
                        alpha=alpha,
                        beta=beta,
                        iterations=iterations,
                        random_seed=random_state
                    )

                    model = malletmodel2ldamodel(mallet_model)

                    cm = CoherenceModel(model=model, texts=list(
                        texts), dictionary=dictionary, coherence=coherence)
                    score = cm.get_coherence()

                    # compute perplexity for this model
                    try:
                        per_word_bound = model.log_perplexity(bow_corpus)
                        perp = float(np.exp(-per_word_bound))
                    except Exception:
                        perp = float('nan')

                    tuning_records.append({
                        'num_topics': int(num_topics),
                        'alpha': float(alpha),
                        'beta': float(beta),
                        'coherence': float(score),
                        'perplexity': perp
                    })

                    logger.info(
                        f"K={num_topics} alpha={alpha} beta={beta} coherence={score:.4f} perp={perp:.4f}")

                    if score > best_score:
                        best_score = score
                        best_model = model
                        best_config = {
                            "num_topics": num_topics,
                            "alpha": alpha,
                            "beta": beta,
                            "random_seed": random_state,
                            "coherence": score,
                            "perplexity": perp,
                        }

                except Exception as e:
                    logger.exception(
                        "Tuning failed for configuration", exc_info=e)

    if best_model is None:
        raise RuntimeError("No model could be trained in tuning")

    # Save best artifacts
    try:
        best_model.save(str(model_path / TRAINED_LDA))
        dictionary.save(str(model_path / TRAINED_DCT))
        MmCorpus.serialize(str(model_path / TRAINED_BOW), bow_corpus)
        meta_path = str(
            Path(model_path / TRAINED_LDA).with_suffix(".meta.json"))
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(best_config, mf, indent=2)
        logger.info("Best tuned model saved")
    except Exception:
        logger.exception("Failed to save best tuned model artifacts")

    return best_model, best_config


def run(name: str, main_topic: str = None, mode: str = None):
    if mode is None:
        mode = os.environ.get('LDA_MODE', 'search')

    if main_topic:  # For get subtopics
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
        tuning=(mode == 'tune'),
        topic_range=DEFAULT_TOPIC_RANGE
    )


def run_submodels():
    kd = pd.read_json(
        Path(MODELS / 'main' / 'trained_lda.meta.json'), orient='index').T
    ti = pd.read_json(Path(MODELS / 'main' / 'topic_inference.json'))

    k = kd['num_topics'].item()
    for c in range(int(k)):
        topic = ti.loc[c]['topics']['topic_name']
        run(f't{c}', main_topic=topic)


if __name__ == '__main__':
    run('main2')
