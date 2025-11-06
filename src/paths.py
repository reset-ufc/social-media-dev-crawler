from pathlib import Path


def get_releated_tags_path(site_alias: str) -> Path:
    """Retorna o caminho para o arquivo de tags relacionadas de um site específico."""
    return RELEATED_TAGS_DIR / f"{site_alias}_releated_tags.csv"


QUESTION_TAG = "encryption"
THRE1 = 0.2
THRE2 = 0.01


PROJECT_ROOT = Path(__file__).parent.parent

DUMP = PROJECT_ROOT / "Extraidos dump"
DATA = PROJECT_ROOT / 'data'

PROMPTS_DIR = PROJECT_ROOT / "prompts"
HIERARCHICAL_PROMPTS_DIR = PROMPTS_DIR / "hierarchical"
FLAT_PROMPTS_DIR = PROMPTS_DIR / "flat"

DATA_MINING = DATA / "data_mining"
DATA_MINING_S1 = DATA_MINING / "s1"
DATA_MINING_S2 = DATA_MINING / "s2"

DUMP_MINING_LOG_FILE = DATA_MINING / "data_mining.log"


SITES = {
    "stackoverflow": "stackapps.com.7z",
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

LLM_CLASSIFICATION = LLM_INFERENCE / "classification"
LLM_SUMMARIZATION = LLM_INFERENCE / "summarization"


MISUSE_CASES_POSTS = LLM_CLASSIFICATION / "misuse_cases_posts.json"

CODE_ANALYSIS = LLM_CLASSIFICATION / "code_analysis.json"
CODE_JUDGEMENT = LLM_CLASSIFICATION / "code_judgement.json"
MERGED_LLM_RESULTS = LLM_CLASSIFICATION / "merged_llm_results.json"

CODE_ANALYSIS_SUMMARY = LLM_SUMMARIZATION / "code_analysis_summary.log"
CODE_JUDGEMENT_SUMMARY = LLM_SUMMARIZATION / "judgement_summary.log"
MERGE_SUMMARY = LLM_SUMMARIZATION / "merge_summary.log"


