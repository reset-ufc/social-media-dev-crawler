import os


BASE_DIR = "./Extraidos dump"
DATA = './data'
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

DUMP_POST_PATH = os.path.join(BASE_DIR, "Posts.xml")

COARSE_QUESTIONS = os.path.join(DATA, "questions_dump.csv")

RELEATED_TAGS = os.path.join(DATA, "releated_tags.csv")
RELEATED_POSTS = os.path.join(DATA, "releated_posts.csv")

FILTRED_POSTS = os.path.join(DATA, "filtred_posts.csv")

CONNECTED_POSTS = os.path.join(DATA, "connected_posts.csv")
PREPROCESSED_POSTS = os.path.join(DATA, "preprocessed_full_posts.csv")

MISUSE_CASES = os.path.join(DATA, "misuse_cases.json")

THRE1 = 0.1
THRE2 = 0.01
