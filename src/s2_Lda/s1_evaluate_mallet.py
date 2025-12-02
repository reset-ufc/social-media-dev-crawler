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


load_dotenv()

# silence noisy ldamodel warnings coming from gensim internals
_logging.getLogger('gensim.models.ldamodel').setLevel(_logging.ERROR)

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def train_mallet_with_beta(
    mallet_path,
    corpus,
    id2word,
    num_topics,
    alpha,
    beta,
    iterations,
    random_seed,
    workers=4,
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
    
    logger.info(f"Training MALLET LDA: topics={num_topics}, alpha={alpha}, beta={beta}, seed={random_seed}")
    
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
    topic_range: Iterable[int] = range(2, 9),
    iterations: int = 100,
    coherence: str = 'c_v',
    beta: float = 0.01,
    random_seed: int = 7562
) -> Tuple[LdaModel, dict]:

    mallet_home = os.environ.get("MALLET_HOME", "/opt/mallet")
    mallet_path = os.path.join(mallet_home, "bin", "mallet")

    if not os.path.exists(mallet_path):
        raise RuntimeError(f"Mallet binary not found at {mallet_path}")

    best_score = float('-inf')
    best_model = None
    best_config = None

    topic_range = list(topic_range) 
    scores = []

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

            cm = CoherenceModel(model=model, texts=list(texts), dictionary=dictionary, coherence=coherence)
            score = cm.get_coherence()
            scores.append(score)

            logger.info(f"num_topics={num_topics} | alpha={alpha} | beta={beta} | seed={random_seed} | coherence={score:.4f}")

            if score > best_score:
                best_score = score
                best_model = model
                best_config = {
                    "num_topics": num_topics, 
                    "alpha": alpha, 
                    "beta": beta,
                    "random_seed": random_seed,
                    "coherence": score
                }

        except Exception as e:
            logger.exception("Model training failed for configuration", exc_info=e)

    if best_model is None:
        raise RuntimeError("No model could be trained")
    else:
        plt.figure(figsize=(10, 6))
        plt.plot(topic_range, scores, marker='o', linestyle='-', color='blue')
        plt.title('Score de Coerência (C_V) por Número de Tópicos')
        plt.xlabel('Número de Tópicos (K)')
        plt.ylabel(f'Score de Coerência ({coherence})')
        plt.xticks(topic_range)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.savefig(str(model_path/'coherence_plot.png'))
        logger.info(f"Coherence plot saved")
        
    return best_model, best_config


def evaluate_model(
    texts: Iterable[List[str]],
    model_path: Path,
    no_below: int = 5,
    no_above: float = 0.5,
    topic_range: Iterable[int] = range(2, 9),
    use_search: bool = True,
    iterations: int = 150,
    random_state: int = 7562, 
    lda_num_topics: Optional[int] = None,
    lda_alpha: Optional[float] = None,
    lda_beta: Optional[float] = 0.01, 
):
    # resolve MALLET
    mallet_home = os.environ.get('MALLET_HOME', r'C:\mallet')
    mallet_path = os.path.join(mallet_home, "bin", "mallet")

    # Start model folder
    model_path.mkdir(parents=True, exist_ok=True)

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
            model_path=model_path,
            topic_range=topic_range,
            iterations=max(50, iterations // 2),
            beta=lda_beta,
            random_seed=random_state
        )

    else:
        num_topics = int(lda_num_topics or (sum(topic_range) / len(topic_range)))
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

        best_config = {
            "num_topics": num_topics, 
            "alpha": alpha,
            "beta": lda_beta,
            "random_seed": random_state
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


def run(name: str, main_topic: str = None):
    if main_topic:  # For get subtopics
        df = pd.read_csv(str(CLASSIFIED_POSTS))
        qids = df[df['topic'] == main_topic]['question_id']
        df = df[df['question_id'].isin(qids)]
    else:
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

    evaluate_model(
        texts,
        MODELS / name,
        lda_beta=0.01, 
        use_search=True,
        topic_range=range(1, 20+1)
    )

if __name__ == '__main__':
    #run('main')
    kd = pd.read_json(Path(MODELS / 'main' / 'trained_lda.meta.json'), orient='index').T
    ti = pd.read_json(Path(MODELS / 'main' / 'topic_inference.json'))

    k = kd['num_topics'].item()
    for c in range(int(k)):
        topic = ti.loc[c]['topics']['topic_name']
        run(f't{c}', main_topic=topic)
    