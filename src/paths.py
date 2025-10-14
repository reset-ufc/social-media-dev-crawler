from pathlib import Path


BASE_DIR = Path("./Extraidos dump")
DATA = Path('./data')
QUESTION_TAG = "encryption"

SITES = {
    "stackoverflow": "stackapps.com.7z",
    "crypto": "crypto.stackexchange.com.7z",
    "security": "security.stackexchange.com.7z"
}

QUESTION_TAGS = {
    "stackoverflow": [QUESTION_TAG],
    "crypto": [QUESTION_TAG],
    "security": [QUESTION_TAG]
}

DUMP_POST_PATH = BASE_DIR / "Posts.xml"

COARSE_QUESTIONS = DATA / "questions_dump.csv"

RELEATED_TAGS = DATA / "releated_tags.csv"
RELEATED_POSTS = DATA / "releated_posts.csv"

FILTRED_POSTS = DATA / "filtred_posts.csv"

CONNECTED_POSTS = DATA / "connected_posts.csv"
PREPROCESSED_POSTS = DATA / "preprocessed_full_posts.csv"

LLM_INFERENCE = DATA / "llm_inference"

MISUSE_CASES = LLM_INFERENCE / "misuse_cases.json"
JUDGEMENT = LLM_INFERENCE / 'judgement.json'

THRE1 = 0.1
THRE2 = 0.01
