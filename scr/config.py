import os

QUESTION_TAG = "encryption"
QUESTION_TAG = "discussion"
BASE_DIR = "./dump"
DATA = './data'


SITES = {
    "stackoverflow": "stackoverflow.com",
    "crypto": "crypto.stackexchange.com",
    "security": "security.stackexchange.com"
}

QUESTION_TAGS = {
    "stackoverflow": [QUESTION_TAG],
    "crypto": ["encryption", "rsa"],
    "security": ["encryption", "rsa"]
}


DUMP_POST_PATH = os.path.join(BASE_DIR, "Posts.xml")
COARSE_PATH = os.path.join(DATA, "coarse")

RELEATED_TAGS = os.path.join(DATA, 'releated_tags.json')

QUESTIONS_CSV = os.path.join(COARSE_PATH, "questions_dump.csv")
ANSWERS_CSV = os.path.join(COARSE_PATH, "answers_dump.csv")
COMMENTS_CSV = os.path.join(COARSE_PATH, "comments_dump.csv")

RELEATED_TAGS =  os.path.join(DATA, "releated_tags.csv")
