# gmm predict script but for genetic derived vars only
# just need: PRS, id, og_id, class data

import numpy as np
import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import pyreadr
import sklearn
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn import tree
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score
import scipy.stats as stats
import statsmodels.api as sm
from pathlib import Path
from sklearn import preprocessing


# reading in smfq data, previously cleaned and scores calculated in R script
df = pyreadr.read_r('/Users/poppygrimes/Library/CloudStorage/OneDrive-UniversityofEdinburgh/Edinburgh/gmm/gmm_alspac/alspac_dep_long.rds')
print(df.keys()) #check which objects we have: there is only None
df = df[None]
df['id'].nunique() #check 15,645

# convert to wide - remember to only use first 4 time points in mplus
df = df[['id','time','dep']]
df_wide = pd.pivot(df, index=['id'], columns='time', values='dep') #should have 15,645 rows
df_wide = df_wide.fillna('-9999') #replace NaNs with -9999 for mplus
filepath = Path('/Users/poppygrimes/Library/CloudStorage/OneDrive-UniversityofEdinburgh/Edinburgh/gmm/gmm_alspac/mplus_data/alspac_smfq_wide_python.txt')
filepath.parent.mkdir(parents=True, exist_ok=True)
df_wide.to_csv(filepath, header=False, sep='\t')  #save wide data for mplus in gmm_abcd directory

# =================================================
# make new df with id, unique id, Xvars and yclass
alspac_4k = pd.read_table('/Users/poppygrimes/Library/CloudStorage/OneDrive-UniversityofEdinburgh/Edinburgh/gmm/gmm_alspac/mplus_data/4k_alspac_smfq.txt', delim_whitespace=True, header=None)  # this is just test will need to change
alspac_4k.columns = ['y0','y1','y2','y3','v1','v2','v3','v4','v5','v6','v7','v8','v9','v10','class','id']
alspac_4k = alspac_4k[['id','class']] #subsetting
alspac_4k.replace('*', np.nan) #replace missing
# merge class with smfq data -
data = pd.merge(df, alspac_4k, on=["id"])
# n8787 unique ids x 11 time points and classes - exclude after 4 time points as this is what model was built on
data = data[data["time"] < 5]

# ===================== EXTRACTING VARS ====================

alspac = pd.read_stata("/Volumes/cmvm/scs/groups/ALSPAC/data/B3421_Whalley_04Nov2021.dta")
als = alspac # call again if need clean

# select only cols we want
als_cols = ['cidB3421','qlet','kz021','c804']
als = als[als_cols]

# make alspac have same ids as originally coded in R
als['cidB3421'] = als['cidB3421'].astype(int)
als['IID'] = als['cidB3421'].astype(str).str.cat(als['qlet'], sep='')
als['id'] = als['cidB3421'].astype(str) + als['qlet']
als = als.drop(['cidB3421', 'qlet'], axis=1)
als['id'] = pd.factorize(als['id'])[0] + 1  # makes ids unique and numeric, should be 15,645
als = als.rename(columns={'kz021':'sex', 'c804':'ethnicity'}) # rename some cols
column_to_move = als.pop("id") # moving id to first col
als.insert(0, "id", column_to_move) # insert column with insert(location, column_name, column_value)


# =============================== appending PRS scores ========================================

# for MDD3
prs_mdd = pd.read_csv('/Users/poppygrimes/Library/CloudStorage/OneDrive-UniversityofEdinburgh/Edinburgh/prs/prs_alspac_OUT/abcd_mdd_prs_230302.best', sep='\s+')
prs_mdd = prs_mdd[['IID', 'PRS']]
als2 = pd.merge(als, prs_mdd, on='IID', how='left')


# ==============================================================================================
# ================================= appending class data =======================================


# make ids same object type - both integers
# alspac_4k is a df of ids and classes (8787 x 2)
# merge als with alspac_4k by id [but need to make sure these IDs are the same
alspac_4k['id'] = alspac_4k['id'].astype(int) # only id and class
df = pd.merge(alspac_4k, als2, on=["id"])

# select and clean variables
dem_vars = ['id', 'IID', 'ethnicity', 'class']
g_vars = ['PRS']
b_vars = ['sex']
all_vars = dem_vars + g_vars + b_vars
X_vars = g_vars + b_vars

# ==========================================================================================
# ================================= MAKING DESIGN MATRIX ===================================

df = df[all_vars] # select only vars we want

# binary vars restrict to [0,1,NaN]
df['sex'] = df['sex'].replace(['Female','Male'], [1,0]) # first recode sex
df[b_vars] = df[b_vars].mask(~df[b_vars].isin([0,1]))

# standardise PRS
df['PRS_std'] = preprocessing.scale(df['PRS'])


# ============================= MN log reg =====================================

# Filter out rows with missing values in 'prs_mdd' and 'class' columns
df2 = df.dropna(subset=['PRS_std', 'class'])
df3 = df2.drop_duplicates(subset=["id"]) # as data is in long format

df3.loc[:, 'class'] = df3['class'].replace(3.0, 0.0) # replace with 0 for ref level
x = df3['PRS_std']
y = df3['class']
X = sm.add_constant(x)
model = sm.MNLogit(y, X)
result = model.fit()
print(result.summary())


