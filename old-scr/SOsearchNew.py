import os
from pprint import pprint
import requests
import pandas as pd
import numpy as np
import time
import csv
import datetime


personal_token = "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"
github_token = os.getenv('GITHUB_TOKEN', personal_token)
github_headers = {'Authorization': f'token {github_token}'}

desired_width = 640
pd.set_option('display.width', desired_width)
np.set_printoptions(linewidth=desired_width)
pd.set_option('display.max_columns', 25)

key = "rl_J7pzw9qHytdmEgM2VvSN5A2sk"

STACKEXCHANGE = "https://api.stackexchange.com/"
VERSION = "2.3/"
endpoint = STACKEXCHANGE + VERSION + 'search/advanced'

question_features = ['site', 'tag', 'question_id', 'accepted_answer_id', 'answer_count', 'creation_date', 'is_answered',
                     'last_activity_date', 'last_edit_date', 'owner_id', 'owner_reputation', 'score', 'view_count',
                     'title', 'body']
answer_features = ['site', 'tag', 'answer_id', 'question_id', 'comment_count', 'creation_date', 'is_accepted',
                   'last_activity_date', 'owner_reputation', 'owner_id', 'score', 'body']
comment_features = ['site', 'tag', 'comment_id', 'post_id', 'creation_date', 'edited', 'owner_reputation', 'owner_id', 'score',
                    'body']


def initiateCSVs():
    if not os.path.exists('questions.csv'):
        with open('questions.csv', 'w', encoding="utf-8", newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(question_features)
    if not os.path.exists('answers.csv'):
        with open('answers.csv', 'w', encoding="utf-8", newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(answer_features)
    if not os.path.exists('comments.csv'):
        with open('comments.csv', 'w', encoding="utf-8", newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(comment_features)

<<<<<<< HEAD:scr/SOsearchNew.py

def save_comments_data(comments, tool, existing_comment_ids):
=======
def save_comments_data(comments, tool, site, existing_comment_ids):
>>>>>>> f9deef23dd64c67630260a6c619af5ae3ebb27b0:SOsearchNew.py
    with open('comments.csv', 'a', encoding="utf-8", newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        for comment in comments:
            c_id = comment.get('comment_id')
            if c_id in existing_comment_ids:
                continue
            existing_comment_ids.add(c_id)

            comment_data = [
                site,
                tool,
                c_id,
                comment.get('post_id', np.nan),
                datetime.datetime.fromtimestamp(comment['creation_date']).strftime(
                    '%Y/%m/%d, %H:%M:%S') if 'creation_date' in comment else np.nan,
                comment.get('edited', False),
                comment.get('owner', {}).get('reputation', np.nan),
                comment.get('owner', {}).get('user_id', np.nan),
                comment.get('score', np.nan),
                comment.get('body', np.nan)
            ]
            writer.writerow(comment_data)

<<<<<<< HEAD:scr/SOsearchNew.py

def getStackOverFlowDataset(toollist):

    # Carrega IDs existentes para evitar duplicatas
=======
def getStackOverFlowDataset(toollist, site='stackoverflow'):
>>>>>>> f9deef23dd64c67630260a6c619af5ae3ebb27b0:SOsearchNew.py
    existing_q_ids = set()
    existing_a_ids = set()
    existing_comment_ids = set()

    if os.path.exists("questions.csv"):
        try:
            df_existing = pd.read_csv("questions.csv")
            existing_q_ids = set(
                df_existing['question_id'].dropna().astype(int))
        except Exception as e:
            print(e)

    if os.path.exists("answers.csv"):
        try:
            df_existing = pd.read_csv("answers.csv")
            existing_a_ids = set(df_existing['answer_id'].dropna().astype(int))
        except Exception as e:
            print(e)

    if os.path.exists("comments.csv"):
        try:
            df_existing = pd.read_csv("comments.csv")
            existing_comment_ids = set(
                df_existing['comment_id'].dropna().astype(int))
        except Exception as e:
            print(e)

    paramsorigin = {
        "key": key,
        "pagesize": 100,
        "sort": "votes",
        "site": site,
        "filter": "!LGdawXSMGS0H5KeF1E6_cH"
    }

    theQuery = STACKEXCHANGE + VERSION + 'search/advanced'
    tag_query = ';'.join(toollist)
    print(f"----> [{site}] Buscando por tags: {tag_query}")

    page = 1
    has_more = True

    while has_more:
        params = paramsorigin.copy()
        params['tagged'] = tag_query
        params['page'] = page

        print(f"----> Página {page}")
        try:
            response = requests.get(theQuery, params=params)
            if response.status_code != 200:
                print(f"Erro HTTP {response.status_code}: {response.text}")
                break

            thejson = response.json()
            questionslist = thejson.get('items', [])
            if not questionslist:
                print("Nenhuma pergunta nesta página.")
                break

            for question in questionslist:
                q_id = question.get('question_id')
                if q_id in existing_q_ids:
                    continue
                existing_q_ids.add(q_id)

                questionitem = [
                    site,
                    tag_query,
                    q_id,
                    question.get('accepted_answer_id', np.nan),
                    question.get('answer_count', 0),
                    datetime.datetime.fromtimestamp(
                        question['creation_date']).strftime('%Y/%m/%d, %H:%M:%S'),
                    question.get('is_answered', False),
                    datetime.datetime.fromtimestamp(question.get('last_activity_date', 0)).strftime(
                        '%Y/%m/%d, %H:%M:%S') if 'last_activity_date' in question else np.nan,
                    datetime.datetime.fromtimestamp(question.get('last_edit_date', 0)).strftime(
                        '%Y/%m/%d, %H:%M:%S') if 'last_edit_date' in question else np.nan,
                    question.get('owner', {}).get('user_id', np.nan),
                    question.get('owner', {}).get('reputation', np.nan),
                    question.get('score', np.nan),
                    question.get('view_count', np.nan),
                    question.get('title', ''),
                    question.get('body', '')
                ]

                with open('questions.csv', 'a', encoding="utf-8", newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(questionitem)

                if 'answers' in question:
                    for answer in question['answers']:
                        a_id = answer.get('answer_id')
                        if a_id in existing_a_ids:
                            continue
                        existing_a_ids.add(a_id)

                        answeritem = [
                            site,
                            tag_query,
                            a_id,
                            answer.get('question_id'),
                            answer.get('comment_count', 0),
                            datetime.datetime.fromtimestamp(
                                answer['creation_date']).strftime('%Y/%m/%d, %H:%M:%S'),
                            answer.get('is_accepted', False),
                            datetime.datetime.fromtimestamp(answer.get('last_activity_date', 0)).strftime(
                                '%Y/%m/%d, %H:%M:%S') if 'last_activity_date' in answer else np.nan,
                            answer.get('owner', {}).get('reputation', np.nan),
                            answer.get('owner', {}).get('user_id', np.nan),
                            answer.get('score', np.nan),
                            answer.get('body', '')
                        ]

                        with open('answers.csv', 'a', encoding="utf-8", newline='') as csvfile:
                            writer = csv.writer(csvfile)
                            writer.writerow(answeritem)

                        if 'comments' in answer:
<<<<<<< HEAD:scr/SOsearchNew.py
                            save_comments_data(
                                answer['comments'], tag_query, existing_comment_ids)

                if 'comments' in question:
                    save_comments_data(
                        question['comments'], tag_query, existing_comment_ids)
=======
                            save_comments_data(answer['comments'], tag_query, site, existing_comment_ids)

                if 'comments' in question:
                    save_comments_data(question['comments'], tag_query, site, existing_comment_ids)
>>>>>>> f9deef23dd64c67630260a6c619af5ae3ebb27b0:SOsearchNew.py

            has_more = thejson.get("has_more", False)
            page += 1
            time.sleep(1)

        except Exception as e:
            print(f"Erro inesperado: {e}")
            break


initiateCSVs()

# Tagas Stack Overflow
getStackOverFlowDataset(["python","encryption","rsa"], site="stackoverflow") #testar o ssl,openssl, esta em toda a web
# Tags Crypto Stack Exchange
getStackOverFlowDataset(["encryption","rsa"], site="crypto")
# tags Security Stack Exchange
getStackOverFlowDataset(["encryption","rsa"], site="security")
