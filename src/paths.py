from pathlib import Path


# Using: https://archive.org/details/stackexchange_20251231


QUESTION_TAG = "cryptography"
QUESTION_TAG_CRYPTO = "encryption"

THRES = {
    "stackoverflow": (0.05, 0.002),
    "crypto": (0.1, 0.001),
    "security": (0.05, 0.002)
}

PROJECT_ROOT = Path(__file__).parent.parent

DUMP = PROJECT_ROOT / "Extraidos dump"
DATA = PROJECT_ROOT / 'data'


DATA_MINING = DATA / "data_mining"
DATA_MINING_S1 = DATA_MINING / "s1"
DATA_MINING_S2 = DATA_MINING / "s2"

DUMP_MINING_LOG_FILE = DATA_MINING / "data_mining.log"

SITES = {
    "stackoverflow": "stackoverflow.com.7z",
    "crypto": "crypto.stackexchange.com.7z",
    "security": "security.stackexchange.com.7z",
}

QUESTION_TAGS = {
    "stackoverflow": [QUESTION_TAG],
    "crypto": [QUESTION_TAG_CRYPTO],  
    "security": [QUESTION_TAG],
}

DUMP_POST_PATH = DUMP / "Posts.xml"

COARSE_QUESTIONS = DATA_MINING_S1 / "questions_dump.csv"
COARSE_QUESTIONS_CRYPTO = DATA_MINING_S1 / "questions_dump_crypto.csv"

R_TAGS = DATA_MINING_S1 / "releated_tags.csv"
R_TAGS_CRYPTO = DATA_MINING_S1 / "releated_tags_crypto.csv"

MERGED_TAGS = DATA_MINING_S1 / "merged_tags.csv"


FILTRED_POSTS = DATA_MINING_S2 / "filtred_posts.csv"
CONNECTED_POSTS = DATA_MINING_S2 / "connected_posts.csv"


# Prompts

PROMPTS_DIR = PROJECT_ROOT / "prompts"

LDA_TOPICS = PROMPTS_DIR / 'lda_topics.txt'
LDA_SUBTOPICS = PROMPTS_DIR / 'lda_subtopics.txt'


# LDA

LDA_DIR = DATA / 'Lda'
MODELS = LDA_DIR / 'models'

LDA_CSVS = LDA_DIR / 'csvs'

TRAINED_LDA = Path('trained_lda.model')
TRAINED_DCT = Path('trained_dictionary.dict')
TRAINED_BOW = Path('trained_corpus.mm')
LDA_CONFIG = Path('trained_lda.meta.json')
LDA_TOPIC_INFERENCE = Path('topic_inference.json')

CLASSIFIED_POSTS = LDA_CSVS / 'classified_posts.csv'
STRATUM_TABLE = LDA_CSVS / 'stratum_table.csv'
NORMALIZED_POSTS = LDA_CSVS/'normalized_posts.csv'

VALIDATION_SAMPLE = LDA_DIR / 'validation_sample.xlsx'



# final topic names
TOPIC_INFERENCE_DIR = PROJECT_ROOT / 'topic-names'


# rqs
NOTEBOOK_OUTPUTS = DATA / 'notebook_outputs'

# RQ2
FUSED_METADATA = NOTEBOOK_OUTPUTS / 'rq2' / 'csvs' / 'fused_metadata.csv'
KENDAL_CORR  = NOTEBOOK_OUTPUTS / 'rq2' / 'csvs' / 'kendall_correlation_table.csv'
FUSED_PLOT = NOTEBOOK_OUTPUTS / 'rq2' / 'plots' / 'fused_plot.pdf'

#RQ3
LANGUAGES_DISTRIBUTION = NOTEBOOK_OUTPUTS / 'rq3' / 'plots' / 'languages_distribution.pdf'
