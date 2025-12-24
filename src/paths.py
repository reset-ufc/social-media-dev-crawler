from pathlib import Path


# Using: https://archive.org/details/stackexchange_20250930


def get_releated_tags_path(site_alias: str) -> Path:
    """Retorna o caminho para o arquivo de tags relacionadas de um site específico."""
    return RELEATED_TAGS_DIR / f"{site_alias}_releated_tags.csv"


QUESTION_TAG = "encryption"

#QUESTION_TAG = "cryptography"

THRE1 = 0.2
THRE2 = 0.01

DIF_CONFIDENCE_THRESHOLD = 0.5

PROJECT_ROOT = Path(__file__).parent.parent

DUMP = PROJECT_ROOT / "Extraidos dump"
DATA = PROJECT_ROOT / 'data'

PROMPTS_DIR = PROJECT_ROOT / "prompts"
HIERARCHICAL_PROMPTS_DIR = PROMPTS_DIR / "hierarquical"
FLAT_PROMPTS_DIR = PROMPTS_DIR / "flat"

LDA_TOPICS = PROMPTS_DIR / 'lda_topics.txt'
LDA_SUBTOPICS = PROMPTS_DIR / 'lda_subtopics.txt'


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
    "crypto": [QUESTION_TAG],
    "security": [QUESTION_TAG],
}

DUMP_POST_PATH = DUMP / "Posts.xml"

COARSE_QUESTIONS = DATA_MINING_S1 / "questions_dump.csv"

RELEATED_TAGS_DIR = DATA_MINING_S1 / "releated_tags"
RELEATED_TAGS = RELEATED_TAGS_DIR / "releated_tags.csv"  

R_TAGS = DATA_MINING_S1 / "releated_tags.csv"


RELEATED_POSTS = DATA_MINING_S1 / "releated_posts.csv"

FILTRED_POSTS = DATA_MINING_S2 / "filtred_posts.csv"

CONNECTED_POSTS = DATA_MINING_S2 / "connected_posts.csv"
CONNECTED_COMMENTS = DATA_MINING_S2 / "connected_posts_comments.csv"
PREPROCESSED_POSTS = DATA_MINING_S2 / "preprocessed_full_posts.csv"
INVALID_CODES = DATA_MINING_S2 / "invalid_codes.csv"


LLM_INFERENCE = DATA / "llm_inference"

# codes
LLM_CLASSIFICATION = LLM_INFERENCE / "classification"
FLAT_LLM_CLASSIFICATION = LLM_CLASSIFICATION / "flat"
HIER_LLM_CLASSIFICATION = LLM_CLASSIFICATION / "hierarquical"

LLM_SUMMARIZATION = LLM_INFERENCE / "summarization"
FLAT_LLM_SUMMARIZATION = LLM_SUMMARIZATION / "flat"
HIER_LLM_SUMMARIZATION = LLM_SUMMARIZATION / "hierarquical"

FLAT_CODE_ANALYSIS = FLAT_LLM_CLASSIFICATION / "code_analysis.json"
FLAT_CODE_JUDGEMENT = FLAT_LLM_CLASSIFICATION / "code_judgement.json"
FLAT_CODE_ANALYSIS_SUMMARY = FLAT_LLM_SUMMARIZATION / "code_analysis_summary.log"
FLAT_MERGED_LLM_RESULTS = FLAT_LLM_CLASSIFICATION / "merged_llm_results.json"
FLAT_MERGED_SUMMARY = FLAT_LLM_SUMMARIZATION / "merge_summary.log"

HIER_CODE_DETECTION = HIER_LLM_CLASSIFICATION / "code_detection.json"
HIER_CODE_TYPE = HIER_LLM_CLASSIFICATION / "code_type.json"
HIER_CODE_FULL_CLASSIFICATION = HIER_LLM_CLASSIFICATION / "full_classification.json"
HIER_CODE_JUDGEMENT = HIER_LLM_CLASSIFICATION / "code_judgement.json"
HIER_CODE_ANALYSIS_SUMMARY = HIER_LLM_SUMMARIZATION / "code_analysis_summary.log"
HIER_MERGED_LLM_RESULTS = HIER_LLM_CLASSIFICATION / "merged_llm_results.json"
HIER_MERGED_SUMMARY = HIER_LLM_SUMMARIZATION / "merge_summary.log"


VALIDATION_SHEET = LLM_INFERENCE / "validation_sheet.xlsx"


# s3 LDA

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