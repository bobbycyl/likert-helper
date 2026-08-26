import numpy as np
import pandas as pd

np.random.seed(42)

N_SAMPLES = 10
N_ITEMS = 40

data = np.random.normal(loc=32, scale=7, size=(N_ITEMS, N_SAMPLES))

df = pd.DataFrame(data.T, columns=[f'Q{i+1}' for i in range(N_ITEMS)])
df = df / 10
df = df.round()
df = df.clip(lower=1, upper=5)
df = df.astype(int)
df.to_csv("40_5_32_7.csv", index=True)

# 检验每一列的均值和标准差
for col in df.columns:
    print(f"{col} 均值: {df[col].mean()}, 标准差: {df[col].std()}")
