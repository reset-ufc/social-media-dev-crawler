from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

PROMPTS_DIR = PROJECT_ROOT / "prompts"

BASE_DIR = PROJECT_ROOT / "Extraidos dump"
DATA = PROJECT_ROOT / 'data'

LOGS_DIR = DATA / "logs"
DUMP_MINING_LOG_FILE = LOGS_DIR / "data_mining.log"

QUESTION_TAG = "encryption"

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

DUMP_POST_PATH = BASE_DIR / "Posts.xml"

COARSE_QUESTIONS = DATA / "questions_dump.csv"

RELEATED_TAGS_DIR = DATA / "releated_tags"
RELEATED_TAGS = RELEATED_TAGS_DIR / \
    "all_releated_tags.csv"  # Consolidado (opcional)


def get_releated_tags_path(site_alias: str) -> Path:
    """Retorna o caminho para o arquivo de tags relacionadas de um site específico."""
    return RELEATED_TAGS_DIR / f"{site_alias}_releated_tags.csv"


RELEATED_POSTS = DATA / "releated_posts.csv"

FILTRED_POSTS = DATA / "filtred_posts.csv"

CONNECTED_POSTS = DATA / "connected_posts.csv"
CONNECTED_COMMENTS = DATA / "connected_posts_comments.csv"
PREPROCESSED_POSTS = DATA / "preprocessed_full_posts.csv"

LLM_INFERENCE = DATA / "llm_inference"

MISUSE_CASES = LLM_INFERENCE / "misuse_cases.json"
JUDGEMENT = LLM_INFERENCE / "judgement.json"

THRE1 = 0.1
THRE2 = 0.01
