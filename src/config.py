import os

BASE_DIR = "C:/Extraidos dump" #C:/Users/ALUNO_UFC/Documents/GitHub/social-media-dev-crawler/Extraidos dump
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
COARSE_PATH = os.path.join(DATA, "coarse")

COARSE_QUESTIONS = os.path.join(COARSE_PATH, "questions_dump.csv")
COARSE_ANSWERS = os.path.join(COARSE_PATH, "answers_dump.csv")
COARSE_COMMENTS = os.path.join(COARSE_PATH, "comments_dump.csv")

RELEATED_TAGS =  os.path.join(DATA, "releated_tags.csv")
RELEATED_POSTS = os.path.join(DATA, "releated_posts.csv")

THRE1 = 0.1
THRE2 = 0.01
