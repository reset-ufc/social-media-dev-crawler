import os
from pprint import pprint
import requests
import requests.auth
import pandas as pd
import numpy as np
import time
import re
import csv
import json
import itertools
from difflib import SequenceMatcher
import datetime
import matplotlib.pyplot as plt
import operator
from nltk.tokenize import sent_tokenize
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from bs4 import BeautifulSoup
import ssl
from urllib.request import urlopen
import glob
import gensim
from gensim.utils import simple_preprocess
import re
import seaborn as sns
from nltk.corpus import stopwords
from time import time
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk.stem.porter import PorterStemmer
from nltk.stem import WordNetLemmatizer
import spacy
from sklearn.datasets import fetch_20newsgroups
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split, StratifiedShuffleSplit
from sklearn.naive_bayes import MultinomialNB
from sklearn import metrics
from pprint import pprint
import tqdm
import gensim.corpora as corpora
from gensim.models import CoherenceModel
from copy import deepcopy
from scipy.sparse import csr_matrix, vstack
from sklearn.naive_bayes import MultinomialNB
from sklearn.naive_bayes import GaussianNB
from scipy.linalg import get_blas_funcs
from sklearn.semi_supervised import LabelPropagation, LabelSpreading
import pprint
from urllib.request import urlopen
from bs4 import BeautifulSoup
from urllib.error import HTTPError, URLError
import datetime
import ssl
import requests
import csv
import urllib
import time
import operator
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering, KMeans
from scipy.stats.stats import pearsonr
from sklearn.metrics import *
import glob
from urllib.request import Request, urlopen
import json
from sklearn.datasets import fetch_20newsgroups
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split, StratifiedShuffleSplit
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import KFold, StratifiedKFold, ShuffleSplit
from sklearn import metrics

desired_width = 320
pd.set_option('display.width', desired_width)
np.set_printoptions(linewidth=desired_width)
pd.set_option('display.max_columns', 25)

monthnumber = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05',
               'Jun': '06', 'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}
now = datetime.datetime.now()
rec = {'Recommended': True, 'Not Recommended': False}
context = ssl._create_unverified_context()
cookies = {'birthtime': '568022401'}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
           'Referer': 'https://steamcommunity.com/', 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}


def fromtextlist2csv(toolappname):
    with open(toolappname+'.txt', 'r', encoding='utf-8') as txtfile:
        linklist = [x.strip('\n') for x in txtfile.readlines()]
    features = ['tag', 'text']
    count = 0
    for item in linklist:
        req = Request(item, headers=headers)
        html = urlopen(req).read()
        bsObj = BeautifulSoup(html, 'lxml')
        thetitle = bsObj.find('h1', {'class': 'article-title'}).get_text()
        thecontent = bsObj.find('div', {'class': 'content-html'}).get_text()
        thetime = bsObj.find('span', {'class': 'author-date'}).get_text()
        thetime = pd.to_datetime(thetime.strip())
        # thetime = pd.to_datetime('20'+thetime.split(', ')[-1]+'-'+monthDict[thetime.split('. ')[0]]+'-'+thetime.split(', ')[0].split('. ')[1])
        with open(f'dzone_{toolappname}.csv', 'a', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow([toolappname, (thetitle + thecontent), thetime])
        count += 1
        print(toolappname+str(count))

# tesintURL = "https://dzone.com/articles/the-origins-of-technical-debt"
# req = Request(tesintURL, headers=headers)
# html = urlopen(req).read()
# bsObj = BeautifulSoup(html, 'lxml')
# thetime = bsObj.find('span', {'class': 'author-date'}).get_text()
# print(pd.to_datetime(thetime.strip()))

# fromtextlist2csv('technical-debt')


x = [0.76, 0.7166666666666667, 0.6928571428571428, 0.69375, 0.6944444444444444, 0.685, 0.759090909090909, 0.725, 0.7269230769230769, 0.7428571428571429, 0.7466666666666667, 0.715625, 0.7617647058823529, 0.7694444444444445, 0.7631578947368421, 0.7825, 0.7738095238095238, 0.7772727272727272, 0.75, 0.78125, 0.778, 0.7730769230769231, 0.7777777777777778, 0.7767857142857143,
     0.7879310344827586, 0.7616666666666667, 0.7758064516129032, 0.778125, 0.7621212121212121, 0.7705882352941177, 0.7628571428571429, 0.7708333333333334, 0.7527027027027027, 0.7657894736842106, 0.7782051282051282, 0.8175, 0.8, 0.805952380952381, 0.8209302325581396, 0.821590909090909, 0.8344444444444444, 0.8195652173913044, 0.8585106382978723, 0.8395833333333333, 0.8397959183673469, 0.843]
y = [0.62, 0.5583333333333333, 0.7142857142857143, 0.5375, 0.5833333333333334, 0.59, 0.6136363636363636, 0.6166666666666667, 0.6115384615384616, 0.6285714285714286, 0.73, 0.590625, 0.638235294117647, 0.6194444444444445, 0.6684210526315789, 0.67, 0.65, 0.6522727272727272, 0.6565217391304348, 0.6666666666666666, 0.69, 0.6865384615384615, 0.6944444444444444, 0.6571428571428571,
     0.6931034482758621, 0.675, 0.6838709677419355, 0.6703125, 0.6772727272727272, 0.6823529411764706, 0.6642857142857143, 0.6805555555555556, 0.6810810810810811, 0.6894736842105263, 0.7, 0.72, 0.7158536585365853, 0.7321428571428571, 0.7430232558139535, 0.7443181818181818, 0.76, 0.7630434782608696, 0.7882978723404256, 0.7802083333333333, 0.789795918367347, 0.793]

for item in y:
    print(item)
