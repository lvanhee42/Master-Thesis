# -*- coding: utf-8 -*-

#
# * Copyright (c) 2009-2017. Authors: see NOTICE file.
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *      http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# */


__author__          = "Vanhee Laurent <laurent.vanhee@student.uliege.ac.be>"
__copyright__       = "Copyright 2010-2017 University of Liège, Belgium, http://www.cytomine.be/"



import csv
import config
from sklearn.ensemble import RandomForestRegressor, AdaBoostRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import cross_val_score
import numpy as np
import matplotlib.pyplot as plt

fusers = open(config.WORKING_DIRECTORY + "gold/learning_data.csv", "rb")
csvoutusers = csv.reader(fusers)
data_users = list(csvoutusers)

ann = data_users.pop(0)

# Remove students that have a result of 0 in our data set
i = 0
while i < len(data_users):
    u = data_users[i]
    if np.float(u[len(u) - 1]) < 0.1:
        del data_users[i]
    else:
        i += 1

# Generate X and Y
X = np.zeros((len(data_users), len(data_users[0]) - 3))
Y = np.zeros(len(data_users))
for i in range(0, len(data_users)):
    u = data_users[i]
    for j in range(0, len(u) - 3):
        X[i][j] = np.float(u[j + 1])
    Y[i] = np.float(u[len(u) - 1])


# To suffle our data set
sample = np.arange(len(X))
np.random.shuffle(sample)

# Use a random forest Regressor
# 2.303
regr = RandomForestRegressor(bootstrap=True, criterion='mse', max_depth=30,
                      max_features='auto', max_leaf_nodes=None,
                      min_impurity_decrease=0.0, min_impurity_split=None,
                      min_samples_leaf=1, min_samples_split=2,
                      min_weight_fraction_leaf=0.0, n_estimators=200, n_jobs=1,
                      oob_score=False, random_state=0, verbose=0, warm_start=False)

#regr = AdaBoostRegressor(DecisionTreeRegressor(max_depth=20), n_estimators=100, random_state=np.random.RandomState(1))
# score 2.417

# fit 70% of our learning sample
regr.fit(X[sample[:int(config.ML_LEARNING_RATIO*len(X))]],Y[sample[:int(config.ML_LEARNING_RATIO*len(X))]])

# predict other 30%
results = regr.predict(X[sample[int(config.ML_LEARNING_RATIO*len(X)):]])

# get 30% expected results to compare
expected = Y[sample[int(config.ML_LEARNING_RATIO*len(X)):]]


# calculate MSQ error and output individual differences
error = 0
for i in range(len(expected)):
    print "Expected " + str(expected[i]) + ", Result " + str(results[i]) + ", Diff " + str(np.abs(results[i] - expected[i]))
    error +=np.abs(results[i] - expected[i]) ** 2

error = np.sqrt(error/len(expected))


# look at feature importance
feat_importance = regr.feature_importances_
print "\n\nFeature Importance"
for i in range(len(feat_importance)):
    print ann[i + 1] + " : " + str(feat_importance[i])

print "\n\nError " + str(error)

avg_cv = 0
cv_scores = cross_val_score(regr, X, Y, cv=len(X), scoring='neg_mean_squared_error')
for i in range(len(cv_scores)):
    cv_scores[i] = np.sqrt(abs(cv_scores[i]))
    avg_cv += cv_scores[i]
avg_cv = avg_cv/len(cv_scores)

print "\n\nCV score :" + str(cv_scores)
print "\n AVG score :" + str(avg_cv)


# plot feature importance
plt.xlabel("Variable Importance")
plt.ylabel("Variable")
plt.title("Importance of Variables used in RF")
feat = [feat_importance[i] for i in range(len(feat_importance))]
x_tics = [i for i in range(len(feat) + 1)]
vars = [ann[i+1] for i in range(len(feat))]
feat.append(0.0)
vars.append("")
plt.xticks(x_tics, vars, rotation=90)
plt.subplots_adjust(bottom=0.3)
plt.hist(x_tics, bins=x_tics, align='left', weights=feat, rwidth=0.4)
plt.grid(True)
plt.show()

