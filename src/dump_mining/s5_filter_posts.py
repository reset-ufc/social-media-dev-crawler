import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import *
from utils import *

percentile = 0.90

questions_q = questions[questions['type'] == 'post'][['answer_count', 'view_count', 'score']].quantile(percentile)

popular_questions = questions[
    (questions['type'] == 'post') &
    (questions['answer_count'] >= questions_q['answer_count']) &
    (questions['view_count'] >= questions_q['view_count']) &
    (questions['score'] >= questions_q['score']) 
]

popular_post_ids = popular_questions['question_id'].unique()

popular_answers = questions[
    (questions['type'] == 'answer') &
    (questions['question_id'].isin(popular_post_ids))
]
