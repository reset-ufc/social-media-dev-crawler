import os

QUESTION_TAG = "encryption"
QUESTION_TAG = "discussion"
BASE_DIR = "./dump"
DATA = './data'

DUMP_POST_PATH = os.path.join(BASE_DIR, "Posts.xml")
COARSE_POST_PATH = os.path.join(DATA, "Posts_coarse.csv")
RELEATED_TAGS = os.path.join(DATA, 'releated_tags.json')