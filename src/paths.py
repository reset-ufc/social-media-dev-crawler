from pathlib import Path


# Using: https://archive.org/details/stackexchange_20251231


QUESTION_TAG = "cryptography"
QUESTION_TAG_CRYPTO = "encryption"

THRE1 = 0.1
THRE2 = 0.002

PROJECT_ROOT = Path(__file__).parent.parent

DUMP = PROJECT_ROOT / "Extraidos dump"
DATA = PROJECT_ROOT / 'data'


DATA_MINING = DATA / "data_mining"
DATA_MINING_S1 = DATA_MINING / "s1"
DATA_MINING_S2 = DATA_MINING / "s2"

# Separate directories for crypto site processing
DATA_MINING_S1_CRYPTO = DATA_MINING / "s1_crypto"
DATA_MINING_S2_CRYPTO = DATA_MINING / "s2_crypto"

DUMP_MINING_LOG_FILE = DATA_MINING / "data_mining.log"

SITES = {
    "stackoverflow": "stackoverflow.com.7z",
    "crypto": "crypto.stackexchange.com.7z",
    "security": "security.stackexchange.com.7z",
}

# Define which tags to search for each site
QUESTION_TAGS = {
    "stackoverflow": [QUESTION_TAG],
    "crypto": [QUESTION_TAG_CRYPTO],  # Uses encryption tag for crypto site
    "security": [QUESTION_TAG],
}

DUMP_POST_PATH = DUMP / "Posts.xml"

# Main questions file (for stackoverflow and security)
COARSE_QUESTIONS = DATA_MINING_S1 / "questions_dump.csv"

# Special output file for crypto site
COARSE_QUESTIONS_CRYPTO = DATA_MINING_S1_CRYPTO / "questions_dump_crypto.csv"

# Related tags files
R_TAGS = DATA_MINING_S1 / "releated_tags.csv"
R_TAGS_CRYPTO = DATA_MINING_S1_CRYPTO / "releated_tags_crypto.csv"

# Merged tags file (manually created by merging R_TAGS and R_TAGS_CRYPTO)
# This file should contain all tags from both standard and crypto processing
MERGED_TAGS = DATA_MINING_S1 / "merged_tags.csv"

# Standard processing files
RELEATED_POSTS = DATA_MINING_S1 / "releated_posts.csv"
FILTRED_POSTS = DATA_MINING_S2 / "filtred_posts.csv"
CONNECTED_POSTS = DATA_MINING_S2 / "connected_posts.csv"
CONNECTED_COMMENTS = DATA_MINING_S2 / "connected_posts_comments.csv"
PREPROCESSED_POSTS = DATA_MINING_S2 / "preprocessed_full_posts.csv"
INVALID_CODES = DATA_MINING_S2 / "invalid_codes.csv"

# Crypto-specific processing files
RELEATED_POSTS_CRYPTO = DATA_MINING_S1_CRYPTO / "releated_posts_crypto.csv"
FILTRED_POSTS_CRYPTO = DATA_MINING_S2_CRYPTO / "filtred_posts_crypto.csv"
CONNECTED_POSTS_CRYPTO = DATA_MINING_S2_CRYPTO / "connected_posts_crypto.csv"
CONNECTED_COMMENTS_CRYPTO = DATA_MINING_S2_CRYPTO / "connected_posts_comments_crypto.csv"
PREPROCESSED_POSTS_CRYPTO = DATA_MINING_S2_CRYPTO / "preprocessed_full_posts_crypto.csv"
INVALID_CODES_CRYPTO = DATA_MINING_S2_CRYPTO / "invalid_codes_crypto.csv"


# Prompts

PROMPTS_DIR = PROJECT_ROOT / "prompts"

LDA_TOPICS = PROMPTS_DIR / 'lda_topics.txt'
LDA_SUBTOPICS = PROMPTS_DIR / 'lda_subtopics.txt'


# LDA

LDA_DIR = DATA / 'Lda'
MODELS = LDA_DIR / 'models'

LDA_CSVS = LDA_DIR / 'csvs'
LDA_PLOTS = LDA_DIR / 'plots'

TRAINED_LDA = Path('trained_lda.model')
TRAINED_DCT = Path('trained_dictionary.dict')
TRAINED_BOW = Path('trained_corpus.mm')
LDA_CONFIG = Path('trained_lda.meta.json')
LDA_TOPIC_INFERENCE = Path('topic_inference.json')

FUSED_METADATA = LDA_CSVS / 'fused_metadata.csv'
CLASSIFIED_POSTS = LDA_CSVS / 'classified_posts.csv'
STRATUM_TABLE = LDA_CSVS / 'stratum_table.csv'
NORMALIZED_POSTS = LDA_CSVS/'normalized_posts.csv'

FUSED_PLOT = LDA_PLOTS / 'fused_plot.png'

VALIDATION_SAMPLE = LDA_DIR / 'validation_sample.xlsx'