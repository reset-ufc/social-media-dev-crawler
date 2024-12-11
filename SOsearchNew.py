import os
from pprint import pprint
import requests
import requests.auth
import pandas as pd
import numpy as np
import time
import csv, json
import itertools
from difflib import SequenceMatcher
import datetime

personal_token = "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"
github_token = os.getenv('GITHUB_TOKEN', personal_token)
github_headers = {'Authorization': f'token {github_token}'}

desired_width = 640
pd.set_option('display.width', desired_width)
np.set_printoptions(linewidth=desired_width)
pd.set_option('display.max_columns', 25)

#key = "89B5kN5OqCqblqKTWBKkjA(("
#key2 = "luNgbAqlXjNtw499eJrSBA(("
key = "rl_J7pzw9qHytdmEgM2VvSN5A2sk"

STACKEXCHANGE = "https://api.stackexchange.com/"
VERSION = "2.3/"
endpoint = STACKEXCHANGE + VERSION + 'search/advanced'
  
question_features = ['tag', 'question_id', 'accepted_answer_id', 'answer_count', 'creation_date', 'is_answered',
                     'last_activity_date', 'last_edit_date', 'owner_id', 'owner_reputation', 'score', 'view_count',
                     'title', 'body']
answer_features = ['tag', 'answer_id', 'question_id', 'comment_count', 'creation_date', 'is_accepted',
                   'last_activity_date', 'owner_reputation', 'owner_id', 'score', 'body']
comment_features = ['tag', 'comment_id', 'post_id', 'creation_date', 'edited', 'owner_reputation', 'owner_id', 'score',
                    'body']

# Function to fetch questions by tags from Stack Overflow
search_tags = ["crypto", "python"]

def fetch_tags_from_stackoverflow(tag, page=1, pagesize=50):
    url = f"https://api.stackexchange.com/2.3/questions"
    params = {
        "order": "desc",
        "sort": "creation",
        "tagged": tag,  # Busca por perguntas relacionadas à tag específica
        "site": "stackoverflow",
        "pagesize": pagesize,
        "page": page
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erro: {response.status_code}, {response.text}")
        return None

def process_tags(data):
    tags = []
    for item in data.get("items", []):
        tags.extend(item.get("tags", []))  # Adiciona todas as tags da pergunta
    return tags

# Script principal
def main():
    all_tags = []
    for search_tag in search_tags:
        print(f"Perguntas com a tag: {search_tag}")
        page = 1
        while True:
            data = fetch_tags_from_stackoverflow(search_tag, page=page)
            if not data or not data.get("items"):
                break
            tags = process_tags(data)
            all_tags.extend(tags)
            if not data.get("has_more"):
                break
            page += 1
            time.sleep(1)  # Evita exceder os limites da API
        
    # Remove duplicatas e organiza as tags
    unique_tags = list(set(all_tags))
    unique_tags.sort()

    # Salva as tags em um arquivo CSV
    if unique_tags:
        df = pd.DataFrame(unique_tags, columns=["Tags"])
        filename = "stackoverflow_tags.csv"
        df.to_csv(filename, index=False)
        print(f"Tags salvas em {filename}")
    else:
        print("Nenhuma tag encontrada.")

if __name__ == "__main__":
    main()  
               
def initiateCSVs():
    with open('questions.csv', 'a', encoding="utf-8", newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(question_features)
    with open('answers.csv', 'a', encoding="utf-8", newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(answer_features)
    with open('comments.csv', 'a', encoding="utf-8", newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(comment_features)

def save_comments_data(comments, tool):
    #comment_features = ['tag', 'comment_id', 'answer_id', 'question_id', 'creation_date', 'edited',
    #                   'owner_reputation', 'owner_id', 'score', 'body']

    with open('comments.csv', 'a', encoding="utf-8", newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        for comment in comments:
            comment_data = [
                tool,  # Tag
                comment.get('comment_id', np.nan),
                #comment.get('answer_id', np.nan),
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


def getStackOverFlowDataset(toollist):
    paramsorigin = {
        "key": key,
        "pagesize": 100,
        "sort": "votes",
        "site": "stackoverflow",
        "filter": "!LGdawXSMGS0H5KeF1E6_cH"
    }
    theQuery = STACKEXCHANGE + VERSION + 'search/advanced'
    for tool in toollist:
        toolsearch = tool
        print("----> " + toolsearch)
        for searcharea in ['title', 'body']:
            print("----> " + searcharea)
            params = paramsorigin.copy()
            has_more = 1
            params['page'] = 0
            params[searcharea] = toolsearch
            while has_more:
                params['page'] = params['page'] + 1
                print("----> Page " + str(params['page']))
                print(theQuery)
                theResult = requests.get(theQuery, params=params)
                thejson = theResult.json()
                #print(thejson)
                questionslist = thejson['items']
                count = 0
                for question in questionslist:
                    count = count + 1
                    print("----> Question " + str(count))
                    questionitem = []
                    #toolname, question_id, accepted_answer_id, answer_count, creation_date,
                    # is_answered, last_activity_date, last_edit_date, owner_id,
                    # owner_reputation, score, view_count, title, body
                    #print(question)
                    questionitem.append(tool)
                    questionitem.append(question['question_id'])
                    try:
                        questionitem.append(question['accepted_answer_id'])
                    except KeyError:
                        questionitem.append(np.nan)
                    questionitem.append(question['answer_count'])
                    questionitem.append(
                        datetime.datetime.fromtimestamp(question['creation_date']).strftime('%Y/%m/%d, %H:%M:%S'))
                    questionitem.append(question['is_answered'])
                    try:
                        questionitem.append(datetime.datetime.fromtimestamp(question['last_activity_date']).strftime(
                            '%Y/%m/%d, %H:%M:%S'))
                    except KeyError:
                        questionitem.append(np.nan)
                    try:
                        questionitem.append(
                            datetime.datetime.fromtimestamp(question['last_edit_date']).strftime('%Y/%m/%d, %H:%M:%S'))
                    except KeyError:
                        questionitem.append(np.nan)
                    try:
                        questionitem.append(question['owner']['user_id'])
                    except KeyError:
                        questionitem.append(np.nan)
                    try:
                        questionitem.append(question['owner']['reputation'])
                    except KeyError:
                        questionitem.append(np.nan)
                    questionitem.append(question['score'])
                    questionitem.append(question['view_count'])
                    questionitem.append(question['title'])
                    questionitem.append(question['body'])

                    if 'comments' in question:
                        save_comments_data(question['comments'], tool)

                    with open('questions.csv', 'a', encoding="utf-8") as csvfile:
                        writer = csv.writer(csvfile, delimiter=',')
                        writer.writerow(questionitem)
                    if question['answer_count'] > 0:
                        answers = question['answers']
                        for answer in answers:
                            # ['toolname', 'answer_id', 'question_id', 'comment_count', 'creation_date', 'is_accepted',
                            # 'last_activity_date', 'owner_reputation', 'owner_id', 'score', 'body']
                            answeritem = []
                            answeritem.append(tool)
                            answeritem.append(answer['answer_id'])
                            answeritem.append(answer['question_id'])
                            answeritem.append(answer['comment_count'])
                            answeritem.append(
                                datetime.datetime.fromtimestamp(answer['creation_date']).strftime('%Y/%m/%d, %H:%M:%S'))
                            answeritem.append(answer['is_accepted'])
                            try:
                                answeritem.append(
                                    datetime.datetime.fromtimestamp(answer['last_activity_date']).strftime(
                                        '%Y/%m/%d, %H:%M:%S'))
                            except KeyError:
                                answeritem.append(np.nan)
                            try:
                                answeritem.append(answer['owner']['reputation'])
                            except KeyError:
                                answeritem.append(np.nan)
                            try:
                                answeritem.append(answer['owner']['user_id'])
                            except KeyError:
                                answeritem.append(np.nan)
                            answeritem.append(answer['score'])
                            answeritem.append(answer['body'])

                            if 'comments' in answer:
                                save_comments_data(answer['comments'], tool)

                            with open('answers.csv', 'a', encoding="utf-8") as csvfile:
                                writer = csv.writer(csvfile, delimiter=',')
                                writer.writerow(answeritem)
                    else:
                        continue
                has_more = thejson['has_more']
            else:
                continue


def getMonth(thestring):
    return '-'.join(str(pd.to_datetime(thestring)).split()[0].split('-')[:2])


initiateCSVs()
getStackOverFlowDataset(["crypto"])
#getStackOverFlowDataset(["python", "crypto"])
#getStackOverFlowDataset(["python;crypto"])
                               

