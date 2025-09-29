import re

import nltk
import pandas as pd
import pyLDAvis
import pyLDAvis.gensim_models as gensimvisualize
from gensim.corpora.dictionary import Dictionary
from gensim.models.coherencemodel import CoherenceModel
from gensim.models.ldamodel import LdaModel
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

nltk.download('stopwords')
nltk.download('wordnet')

swods = stopwords.words('english')
swods.extend([])

lemma = WordNetLemmatizer()