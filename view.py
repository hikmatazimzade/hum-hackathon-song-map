import pandas as pd
import numpy as np


df = pd.read_csv("songs_merged.csv")
nan_num = 0
for r in df.itertuples():
    print(r.full_text)
    print(type(r.full_text))

    if type(r.full_text) == float:
        nan_num += 1

print(f"Nan Num: {nan_num}")
print(f"Len: {len(df)}")