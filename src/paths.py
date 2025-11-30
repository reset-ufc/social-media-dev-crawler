from pathlib import Path


def get_releated_tags_path(site_alias: str) -> Path:
    """Retorna o caminho para o arquivo de tags relacionadas de um site específico."""
    return RELEATED_TAGS_DIR / f"{site_alias}_releated_tags.csv"


QUESTION_TAG = "data-protection"
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
RELEATED_TAGS = RELEATED_TAGS_DIR / \
    "all_releated_tags.csv"  # Consolidado (opcional)


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
NORMALIZED_POSTS = LDA_DIR/'normalized_posts.csv'

MODEL = LDA_DIR / 'model'
TRAINED_LDA = MODEL / 'trained_lda.model'
TRAINED_DCT = MODEL / 'trained_dictionary.dict'
TRAINED_BOW = MODEL / 'trained_corpus.mm'
LDA_VISUALIZATION = MODEL / 'lda_visualization.html'
LDA_CONFIG = MODEL / 'trained_lda.meta.json'

LDA_CSVS = LDA_DIR / 'csvs'
LDA_PLOTS = LDA_TOPICS / 'plots'


FUSED_METADATA = LDA_CSVS / 'fused_metadata.csv'
CLASSIFIED_POSTS = LDA_CSVS / 'classified_posts.csv'
STRATUM_TABLE = LDA_CSVS / 'stratum_table.csv'

FUSED_PLOT = LDA_PLOTS / 'fused_plot.png'


TOPIC_INFERENCE = LDA_DIR / 'topic_inference.json'
VALIDATION_SAMPLE = LDA_DIR / 'validation_sample.xlsx'