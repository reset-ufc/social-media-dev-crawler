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

LOGS_DIR = DATA / "logs"
DUMP_MINING_LOG_FILE = LOGS_DIR / "data_mining.log"

PROMPTS_DIR = PROJECT_ROOT / "prompts"

DATA_MINING = DATA / "data_mining"
DATA_MINING_S1 = DATA_MINING / "s1"
DATA_MINING_S2 = DATA_MINING / "s2"


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

MISUSE_CASES_POSTS = LLM_INFERENCE / "misuse_cases_posts.json"
MISUSE_CASES_CODES = LLM_INFERENCE / "misuse_cases_codes.json"

JUDGEMENT_CODES = LLM_INFERENCE / "judgement_codes.json"
MISUSE_SUMMARY = LLM_INFERENCE / "misuse_summary.csv"
