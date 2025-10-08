import pandas as pd
from config import *


df = pd.read_csv(RELEATED_POSTS)

# Numero de posts capturados
print(df.shape)