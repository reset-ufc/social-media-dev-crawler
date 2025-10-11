import pandas as pd
from paths import *


df = pd.read_csv(RELEATED_POSTS)

# Numero de posts capturados
print(df.shape)