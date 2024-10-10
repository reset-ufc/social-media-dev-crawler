import pprint
from urllib.request import urlopen
from bs4 import BeautifulSoup
from urllib.error import HTTPError, URLError
import datetime
import ssl
import requests
import csv
import os
import urllib
import time
import operator
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering, KMeans
from scipy.stats import pearsonr
from sklearn.metrics import *
import glob
from urllib.request import Request, urlopen
from urllib.error import URLError
import json

desired_width = 320
pd.set_option('display.width', desired_width)
np.set_printoptions(linewidth=desired_width)
pd.set_option('display.max_columns', 25)

monthnumber = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
               'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}
now = datetime.datetime.now()
rec = {'Recommended': True, 'Not Recommended': False}
context = ssl._create_unverified_context()
cookies = {'birthtime': '568022401'}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
    'Referer': 'https://steamcommunity.com/', 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}

testingurl1 = 'https://medium.com/picus-security-engineering/answers-to-faq-about-being-a-software-engineer-in-picus-ec94d3235f6a'
testingurl2 = 'https://medium.com/@a.minaro/the-not-so-simple-life-of-data-scientists-84da4050328'


def readArticleLink(link):
    req = Request(link, headers=headers)
    html = urlopen(req).read()
    # html = urlopen(link, context=context, header = )
    bsObj = BeautifulSoup(html, 'lxml')
    print(bsObj.prettify())


def getArticleIdDateTitle(link):
    req = Request(link, headers=headers)
    html = urlopen(req).read()
    # html = urlopen(link, context=context, header = )
    bsObj = BeautifulSoup(html, 'lxml')
    title = bsObj.find('script', {'type': 'application/ld+json'})
    maintext = title.get_text()
    jsontext = json.loads(maintext)
    return jsontext['identifier'], jsontext['datePublished'], jsontext['headline']

def getArticleDate(link):
    req = Request(link, headers=headers)
    html = urlopen(req).read()
    # html = urlopen(link, context=context, header = )
    bsObj = BeautifulSoup(html, 'lxml')
    title = bsObj.find('script', {'type': 'application/ld+json'})
    maintext = title.get_text()
    jsontext = json.loads(maintext)
    return jsontext['datePublished']


def getArticleContent(link):
    req = Request(link, headers=headers)
    html = urlopen(req).read()
    # html = urlopen(link, context=context, header = )
    bsObj = BeautifulSoup(html, 'lxml')
    content = bsObj.find_all('p', {'class': 'pw-post-body-paragraph'})
    return ' '.join([x.get_text() for x in content])


# let's run this method.
def getArticleUrlListwithTag(thetag):
    theurl = f"https://medium.com/tag/{thetag}/archive"
    req = Request(theurl, headers=headers)
    html = urlopen(req).read()
    bsObj = BeautifulSoup(html, 'lxml')
    years = bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width50'})
    # yearhrefs = [x.find('a').get('href') for x in years]
    # articleurls = []
    with open(f"{thetag}_medium.csv", 'a') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(['id', 'date', 'title', 'text'])
    count = 0
    for year in years:
        year_req = Request(year.find('a').get('href'), headers=headers)
        year_html = urlopen(year_req).read()
        year_bsObj = BeautifulSoup(year_html, 'lxml')
        months = year_bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width80'})
        for month in months:
            try:
                month_req = Request(month.find('a').get('href'), headers=headers)
                month_html = urlopen(month_req).read()
                month_bsObj = BeautifulSoup(month_html, 'lxml')
                days = month_bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width35'})
                for day in days:
                    try:
                        day_req = Request(day.find('a').get('href'), headers=headers)
                        day_html = urlopen(day_req).read()
                        day_bsObj = BeautifulSoup(day_html, 'lxml')
                        urls = [x.get('href') for x in day_bsObj.find_all('a', {
                            'class': 'button button--smaller button--chromeless u-baseColor--buttonNormal'})]
                        # articleurls.extend(urls)
                        for url in urls:
                            tempinput = []
                            theid, thedate, thetitle = getArticleIdDateTitle(url)
                            print(thedate)
                            tempinput.append(theid)
                            tempinput.append(thedate)
                            tempinput.append(thetitle)
                            tempinput.append(getArticleContent(url))
                            with open(f"{thetag}-medium.csv", 'a') as csvfile:
                                writer = csv.writer(csvfile, delimiter=',')
                                writer.writerow(tempinput)
                            count = count + 1
                            print(count)
                        del days
                        del day_req
                        del day_html
                        del day_bsObj
                    except (requests.ConnectionError, requests.Timeout) as exception:
                        print("poor or no internet connection.")
                    except:
                        continue

                del months
                del month_req
                del month_html
                del month_bsObj
            except:
                continue
        del year_req
        del year_html
        del year_bsObj


# This method scrape all medium results of a tag in a predefined year.
def getArticleUrlListwithTagYearCheck(thetag, year_tocheck):
    theurl = f"https://medium.com/tag/{thetag}/archive"
    req = Request(theurl, headers=headers)
    html = urlopen(req).read()
    bsObj = BeautifulSoup(html, 'lxml')
    years = bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width50'})
    with open(f"./results/{thetag}_medium_{year_tocheck}.csv", 'a') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(['id', 'date', 'title', 'text'])
    count = 0
    for year in years:
        year_number = int(year.find('a').get_text())
        if year_number < year_tocheck:
            continue
        else:
            if year_number > year_tocheck:
                break
            print("Analyzing" + year.find('a').get_text())
        year_req = Request(year.find('a').get('href'), headers=headers)
        year_html = urlopen(year_req).read()
        year_bsObj = BeautifulSoup(year_html, 'lxml')
        months = year_bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width80'})
        for month in months:
            try:
                month_req = Request(month.find('a').get('href'), headers=headers)
                month_html = urlopen(month_req).read()
                month_bsObj = BeautifulSoup(month_html, 'lxml')
                days = month_bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width35'})
                for day in days:
                    try:
                        day_req = Request(day.find('a').get('href'), headers=headers)
                        day_html = urlopen(day_req).read()
                        day_bsObj = BeautifulSoup(day_html, 'lxml')
                        urls = [x.get('href') for x in day_bsObj.find_all('a', {
                            'class': 'button button--smaller button--chromeless u-baseColor--buttonNormal'})]
                        for url in urls:
                            tempinput = []
                            theid, thedate, thetitle = getArticleIdDateTitle(url)
                            print(thedate + " is " + int(thedate[0:4]))
                            tempinput.append(theid)
                            tempinput.append(thedate)
                            tempinput.append(thetitle)
                            tempinput.append(getArticleContent(url))
                            with open(f"./results/{thetag}_medium_{year_tocheck}.csv", 'a') as csvfile:
                                writer = csv.writer(csvfile, delimiter=',')
                                writer.writerow(tempinput)
                            count = count + 1
                            print(count)

                        del day_req
                        del day_html
                        del day_bsObj
                    except (requests.ConnectionError, requests.Timeout) as exception:
                        print("poor or no internet connection.")
                    except:
                        continue

                del days
                del month_req
                del month_html
                del month_bsObj
            except:
                continue
        del months
        del year_req
        del year_html
        del year_bsObj


# This method scrape all medium results of a tag in a predefined year and a predefined month.
# doesn't work still
def getArticleUrlListwithTagYearMonthCheck(thetag, year_tocheck,month_tocheck):
    theurl = f"https://medium.com/tag/{thetag}/archive"
    req = Request(theurl, headers=headers)
    html = urlopen(req).read()
    bsObj = BeautifulSoup(html, 'lxml')
    years = bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width50'})

    count = 0
    for year in years:
        year_number = int(year.find('a').get_text())
        if year_number < year_tocheck:
            continue
        else:
            if year_number > year_tocheck:
                return
        if year_number == year_tocheck:
            print(f"Analyzing {year_tocheck}")
        year_req = Request(year.find('a').get('href'), headers=headers)
        year_html = urlopen(year_req).read()
        year_bsObj = BeautifulSoup(year_html, 'lxml')
        months = year_bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width80'})
        for month in months:
                if(month.find('a')== None):
                    continue
                month_number = int(datetime.datetime.strptime(month.find('a').get_text(), "%B").month)
                if month_number != month_tocheck:
                    continue
                if month_number == month_tocheck:
                    print(f"Analyzing Year:{year_number} Month: {month_number}")
                month_req = Request(month.find('a').get('href'), headers=headers)
                month_html = urlopen(month_req).read()
                month_bsObj = BeautifulSoup(month_html, 'lxml')

                days = month_bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width35'})
                with open(
                        f"{get_directory(year_number, month_number)}/{thetag}_medium_{year_tocheck}_{month_number}.csv",
                        'w') as csvfile:
                    writer = csv.writer(csvfile, delimiter=',')
                    writer.writerow(['id', 'date', 'title', 'text'])
                if days:
                    for day in days:
                        try:
                            if (day.find('a') == None):
                                continue
                            day_req = Request(day.find('a').get('href'), headers=headers)
                            day_html = urlopen(day_req).read()
                            day_bsObj = BeautifulSoup(day_html, 'lxml')
                            #select the 'Read More...' objects inside the page
                            urls = [x.get('href') for x in day_bsObj.find_all('a', {
                                'class': 'button button--smaller button--chromeless u-baseColor--buttonNormal'})]
                            # articleurls.extend(urls)
                            for url in urls:
                                tempinput = []
                                theid, thedate, thetitle = getArticleIdDateTitle(url)
                                tempinput.append(theid)
                                tempinput.append(thedate)
                                tempinput.append(thetitle)
                                tempinput.append(getArticleContent(url))
                                with open(
                                        f"{get_directory(year_number, month_number)}/{thetag}_medium_{year_tocheck}_{month_number}.csv",
                                        'a') as csvfile:
                                    writer = csv.writer(csvfile, delimiter=',')
                                    writer.writerow(tempinput)
                                count = count + 1
                                print(count)
                            del day_req
                            del day_html
                            del day_bsObj
                        except (requests.ConnectionError, requests.Timeout) as exception:
                            print("poor or no internet connection.")
                        except:
                            continue

                    del days
                else:
                    #in this case we have that medium doesn't collect data for each day, but collecting all the article in the whole month
                    urls = [x.get('href') for x in month_bsObj.find_all('a', {
                        'class': 'button button--smaller button--chromeless u-baseColor--buttonNormal'})]
                    for url in urls:
                        tempinput = []
                        theid, thedate, thetitle = getArticleIdDateTitle(url)
                        tempinput.append(theid)
                        tempinput.append(thedate)
                        tempinput.append(thetitle)
                        tempinput.append(getArticleContent(url))
                        with open(
                                f"{get_directory(year_number, month_number)}/{thetag}_medium_{year_tocheck}_{month_number}.csv",
                                'a') as csvfile:
                            writer = csv.writer(csvfile, delimiter=',')
                            writer.writerow(tempinput)
                        count = count + 1
                        print(count)
                del month_req
                del month_html
                del month_bsObj
        del months
        del year_req
        del year_html
        del year_bsObj


def getArticleUrlListwithTagContinue(thetag):
    theurl = f"https://medium.com/tag/{thetag}/archive"
    req = Request(theurl, headers=headers)
    html = urlopen(req).read()
    bsObj = BeautifulSoup(html, 'lxml')
    years = bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width50'})
    # yearhrefs = [x.find('a').get('href') for x in years]
    # articleurls = []
    dfexist = pd.read_csv(f"{thetag}-medium.csv")
    existingids = dfexist['id'].values.tolist()
    lastdate = dfexist['date'].values.tolist()[-1]
    lastyear = int(lastdate.split('T')[0].split('-')[0])
    count = 0
    for year in [x for x in years if int(x.find('a').get_text()) >= lastyear]:
        year_req = Request(year.find('a').get('href'), headers=headers)
        year_html = urlopen(year_req).read()
        year_bsObj = BeautifulSoup(year_html, 'lxml')
        months = year_bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width80'})
        for month in months:
            try:
                month_req = Request(month.find('a').get('href'), headers=headers)
                month_html = urlopen(month_req).read()
                month_bsObj = BeautifulSoup(month_html, 'lxml')

                days = month_bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width35'})
                for day in days:
                    try:

                        day_req = Request(day.find('a').get('href'), headers=headers)
                        day_html = urlopen(day_req).read()
                        day_bsObj = BeautifulSoup(day_html, 'lxml')
                        urls = [x.get('href') for x in day_bsObj.find_all('a', {
                            'class': 'button button--smaller button--chromeless u-baseColor--buttonNormal'})]
                        # articleurls.extend(urls)
                        for url in urls:
                            tempinput = []
                            theid, thedate, thetitle = getArticleIdDateTitle(url)
                            if theid in existingids:
                                continue
                            else:
                                tempinput.append(theid)
                                tempinput.append(thedate)
                                tempinput.append(thetitle)
                                tempinput.append(getArticleContent(url))
                                with open(f"{thetag}-medium.csv", 'a') as csvfile:
                                    writer = csv.writer(csvfile, delimiter=',')
                                    writer.writerow(tempinput)
                                count = count + 1
                                print(count)
                    except:
                        continue
                del days
                del month_bsObj
                del month_html
                del month_req
            except:
                continue
        del months
        del year_bsObj
        del year_html
        del year_req


def makeupforbefore():
    years = list(range(2015, 2022))
    for year in years:
        theurl = f"https://medium.com/tag/ai/archive/{year}"
        req = Request(theurl, headers=headers)
        html = urlopen(req).read()
        bsObj = BeautifulSoup(html, 'lxml')
        articles = bsObj.find_all('a', {'class': 'button button--smaller button--chromeless u-baseColor--buttonNormal'})
        for article in articles:
            url = article.get('href')
            tempinput = []
            theid, thedate, thetitle = getArticleIdDateTitle(url)
            tempinput.append(theid)
            tempinput.append(thedate)
            tempinput.append(thetitle)
            tempinput.append(getArticleContent(url))
            with open(f"ai-medium.csv", 'a') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow(tempinput)


# function that return the path of the scraping directory
# if the path doesn't exist it creates it
def get_directory(year, month):
    path = f'./results/{year}/{month}'
    if not os.path.exists(path):
        os.makedirs(path)
    return path

data = {
    'AssignedTo': [],  # Usuários
    'IdRun': [],       # IDs 
    'Year': [],        # O Ano 
    'Month': [],       # Os Meses
    'Tag': [],         # A Tag
    'Completed': []    # Arquivo completo
}

df = pd.DataFrame(data)
df.to_csv('year_tocheck.csv', index=False)
def WebScrapeAssignedMonth(username):
    print(f'Hi {username}!')
    df = pd.read_csv('year_tocheck.csv')
    df_user_part = df[df['AssignedTo'] == username]
    num_df_total = len(df_user_part)
    df_remaining_part = df_user_part[df_user_part['Completed'] == False]
    num_df_remaining = len(df_remaining_part)
    print(f"We have to actually scrape the remaining {num_df_remaining} parts out of {num_df_total}, "
          f"thank you for your support.")
    id_list_to_do = df_remaining_part['IdRun'].values
    for id in id_list_to_do:
        df_line = df_remaining_part[df_remaining_part['IdRun'] == id]
        year = df_line['Year'].values[0]
        tag = df_line['Tag'].values[0]
        month = df_line['Month'].values[0]
        index=month
        print(f'Starting to scrape {tag} in {year}')
        while index<12:
            print(f'Month:{index+1}')
            getArticleUrlListwithTagYearMonthCheck(tag, year,index+1)
            df.loc[id - 1, 'Month'] = index+1
            df.to_csv('year_tocheck.csv', index=False)
            index=index+1
        df.loc[id - 1, 'Completed'] = True
        df.to_csv('year_tocheck.csv', index=False)
        num_df_remaining = num_df_remaining - 1
        print(f"We have completed {year} dataset, now we have only to do {num_df_remaining}")



def WebScrapeAssigned(username):
    print(f'Hi {username}!')
    df = pd.read_csv('year_tocheck.csv')
    df_user_part = df[df['AssignedTo'] == username]
    num_df_total = len(df_user_part)
    df_remaining_part = df_user_part[df_user_part['Completed'] == False]
    num_df_remaining = len(df_remaining_part)
    print(f"We have to actually scrape the remaining {num_df_remaining} parts out of {num_df_total}, "
          f"thank you for your support.")
    id_list_to_do = df_remaining_part['IdRun'].values
    for id in id_list_to_do:
        df_line = df_remaining_part[df_remaining_part['IdRun'] == id]
        year = df_line['Year'].values[0]
        tag = df_line['Tag'].values[0]
        month = df_line['Month'].values[0]
        index=month
        print(f'Starting to scrape {tag} in {year}')
        getArticleUrlListwithTagYearCheck(tag,year)
        df.loc[id - 1, 'Completed'] = True
        df.to_csv('year_tocheck.csv', index=False)
        num_df_remaining = num_df_remaining - 1
        print(f"We have completed {year} dataset, now we have only to do {num_df_remaining}")

WebScrapeAssignedMonth('Rafael')
getArticleUrlListwithTag('technical-dept')
#WebScrapeAssignedMonth('xiaozhou1')

def makeFlagCSV(thetag, user):
    theurl = f"https://medium.com/tag/{thetag}/archive"
    req = Request(theurl, headers=headers)
    html = urlopen(req).read()
    bsObj = BeautifulSoup(html, 'lxml')
    years = bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width50'})
    for item in years:
        print(item)
    count = 0
    with open(f"./{thetag}-medium-flag.csv", 'a') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(['url', 'complete', 'user'])
    for year in years:
        year_req = Request(year.find('a').get('href'), headers=headers)
        year_html = urlopen(year_req).read()
        year_bsObj = BeautifulSoup(year_html, 'lxml')
        months = year_bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width80'})
        if len(months) == 0:
            with open(f"./{thetag}-medium-flag.csv", 'a') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow([year.find('a').get('href'), 0, user])
        else:
            for monthitem in months:
                try:
                    month_req = Request(monthitem.find('a').get('href'), headers=headers)
                    month_html = urlopen(month_req).read()
                    month_bsObj = BeautifulSoup(month_html, 'lxml')
                    days = month_bsObj.find_all('div', {'class': 'timebucket u-inlineBlock u-width35'})
                    if len(days) == 0:
                        with open(f"./{thetag}-medium-flag.csv", 'a') as csvfile:
                            writer = csv.writer(csvfile, delimiter=',')
                            writer.writerow([monthitem.find('a').get('href'), 0, user])
                    else:
                        for dayitem in days:
                            try:
                                with open(f"./{thetag}-medium-flag.csv", 'a') as csvfile:
                                    writer = csv.writer(csvfile, delimiter=',')
                                    writer.writerow([dayitem.find('a').get('href'), 0, user])
                            except:
                                continue
                except:
                    continue

def continueCrawl(thetag, user):
    df_flag = pd.read_csv(f"./{thetag}-medium-flag.csv")
    df_flag_todo = df_flag.loc[(df_flag['complete']==0) & (df_flag['user']==user), :]
    urllist = df_flag_todo['url'].values.tolist()
    dfexist = pd.read_csv(f"{thetag}-medium-3.csv")
    existingids = dfexist['id'].values.tolist()
    count = 0
    for url in urllist:
        print(url)
        day_req = Request(url, headers=headers)
        day_html = urlopen(day_req).read()
        day_bsObj = BeautifulSoup(day_html, 'lxml')
        articles = [x.get('href') for x in day_bsObj.find_all('a', {
            'class': 'button button--smaller button--chromeless u-baseColor--buttonNormal'})]
        #print(articles)
        for article in articles:
            tempinput = []
            try:
                theid, thedate, thetitle = getArticleIdDateTitle(article)
            except:
                continue
            if theid in existingids:
                continue
            else:
                tempinput.append(theid)
                tempinput.append(thedate)
                tempinput.append(thetitle)
                tempinput.append(getArticleContent(article))
                with open(f"{thetag}-medium-3.csv", 'a') as csvfile:
                    writer = csv.writer(csvfile, delimiter=',')
                    writer.writerow(tempinput)
                count = count + 1
                print(count)
        df_flag.loc[df_flag['url']==url, 'complete']=1
        df_flag.to_csv(f"./{thetag}-medium-flag.csv", index=False)
        #break


makeFlagCSV('python', 2022)
#continueCrawl('python', '2022')


