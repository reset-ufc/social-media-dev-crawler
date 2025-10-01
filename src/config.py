import os

BASE_DIR = "./dump"
DATA = './data'


SITES = {
    "stackoverflow": "stackoverflow.com",
    "crypto": "crypto.stackexchange.com",
    "security": "security.stackexchange.com"
}


QUESTION_TAG = "encryption"
QUESTION_TAG = "discussion"


QUESTION_TAGS = {
    "stackoverflow": [QUESTION_TAG],
    "crypto": ["encryption", "rsa"],
    "security": ["encryption", "rsa"]
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
