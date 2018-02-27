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
from sklearn.ensemble import RandomForestRegressor, AdaBoostRegressor, BaggingRegressor, ExtraTreesRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import cross_val_score
import numpy as np
import matplotlib.pyplot as plt
import sys
from matplotlib.patches import Rectangle


def load_data(project):
    """
    Loads the project learning file into memory, generates X and their respective name.
    The file is a CSV file with :
        - 1st row <M | X | Y> to define the variable on the same column
        - 2nd row <var_name>, the name of the variable in the same column
        - 3rd to nth row: Data associated to a student, 1 row per student
    :param project: the project name, E.G GOLD | SILVER
    :return: - data_users : 2D list array containing all file contents
             - X : 2D numpy array containing all the X variables of data_users
             - name_X : list containing names associated to each X variable
    """
    fusers = open(config.WORKING_DIRECTORY + project + "/learning_data.csv", "rb")
    csvoutusers = csv.reader(fusers)
    data_users = list(csvoutusers)

    # Remove students that have a result of 0/20 in our data set
    i = 2
    while i < len(data_users):
        u = data_users[i]
        if np.float(u[len(u) - 1]) < 0.1 or np.float(u[len(u) - 2]) < 0.1:
            del data_users[i]
        else:
            i += 1

    # count the number of X variables to allocate np array
    l_x = 0
    for i in range(len(data_users[0])):
        if data_users[0][i] == 'X':
            l_x += 1
    name_X = []
    X = np.zeros((len(data_users) - 2, l_x))

    # fill the numpy array with variables
    j = 0
    for i in range(0, len(data_users[0])):
        if data_users[0][i] == 'X':
            name_X.append(data_users[1][i])
            for k in range(0, len(data_users) - 2):
                X[k][j] = np.float(data_users[k + 2][i])
            j += 1
    return data_users, X, name_X

def leave_one_out_cv(regr, X, Y):
    """
    Does a leave one out cross validation test. Reimplemented because we also needed the predicted grades not only the scores
    :param regr:
    :param X: input
    :param Y: output
    :return: scores, grades
    """
    scores = []
    grades = []
    for i in range(len(Y)):
        newX = np.delete(np.copy(X), i, 0)
        newY = np.delete(np.copy(Y), i, 0)
        regr.fit(newX, newY)

        x_test = X[i: i + 1]
        y_test = Y[i]
        pred = regr.predict(x_test)

        grades.append(pred[0])
        scores.append((abs(y_test - pred[0])))
    return scores, grades

def build_models(project):
    """
    Builds a FULL model from all the users in the learning file
    This is done for every Y variable (EG practical/theoretical results)
    Outputs a figure showing the variable importance for every Y variable
    :param project: project name
    :return: the list of models (by order of Y variable)
    """
    models = []
    data_users, X, name_X = load_data(project)
    print  len(name_X)
    nb = 1
    for i in range(len(data_users[0])):
        if data_users[0][i] == 'Y':
            Y = np.zeros(len(data_users) - 2)
            for j in range(len(data_users) - 2):
                Y[j] = np.float(data_users[j + 2][i])

            sample = np.arange(len(X))
            np.random.shuffle(sample)
            regr = ExtraTreesRegressor(bootstrap=False, criterion='mse', max_depth=None,
                                  max_features='auto', max_leaf_nodes=None,
                                  min_impurity_decrease=0.0, min_impurity_split=None,
                                  min_samples_leaf=1, min_samples_split=2,
                                  min_weight_fraction_leaf=0.0, n_estimators=10000, n_jobs=1,
                                  oob_score=False, random_state=0, verbose=0, warm_start=False)

            # fill FULL data set
            regr.fit(X, Y)


            # look at feature importance and sort
            feat_importance = regr.feature_importances_
            sorted_args = np.argsort(feat_importance)
            sorted_feat = [feat_importance[sorted_args[len(feat_importance) - j - 1]] for j in range(len(feat_importance))]
            sorted_name = [name_X[sorted_args[len(feat_importance) - j - 1]] for j in range(len(feat_importance))]

            imp_ims = [1227247,1552356,1209160,1205626,1217031,1218337,1200227,1217514,1204731,1216821,
                       1217927,1206962,1204545,1216615,1210048,1205882,1218530,1200409,1213537,1202969,1218942,
                       1212431,1207786,1199971,1219330]

            plot_size = min(80, len(sorted_feat))
            x_tics = [j for j in range(len(sorted_feat) + 1)]
            x_tics = x_tics[0:plot_size + 1]
            sorted_name = sorted_name[0:plot_size]
            sorted_feat = sorted_feat[0:plot_size]

            # plot feature importance
            plt.figure(nb)
            nb += 1

            plt.xlabel("Variable Importance")
            plt.ylabel("Variable")
            plt.title("Importance of Variables used in ML for " + data_users[1][i])

            sorted_feat.append(0.0)
            sorted_name.append("")
            plt.xticks(x_tics, sorted_name, rotation=90, fontsize=8)
            plt.subplots_adjust(bottom=0.3)
            _, _, bars = plt.hist(x_tics, bins=x_tics, align='left', weights=sorted_feat, rwidth=0.4)
            for j in range(0, len(bars)):
                n = sorted_name[j]
                sp = n.split(" ")
                if "AT IMAGE" in n and int(sp[len(sp) - 1]) in imp_ims:
                    bars[j].set_fc('r')
                elif "AT IMAGE" in n and int(sp[len(sp) - 1]) not in imp_ims:
                    bars[j].set_fc('g')
                else:
                    bars[j].set_fc('b')

            # create legend
            handles = [Rectangle((0, 0), 1, 1, color=c, ec="k") for c in ['r', 'g', 'b']]
            labels = ["Important Image vars", "Regular Image vars", "General vars"]
            plt.legend(handles, labels)
            plt.grid(True)


            plt.figure(nb)
            nb += 1
            counter = 0
            c = 230
            for a in range(6):
                c += 1
                plt.subplot(c)
                sc = [X[j][sorted_args[len(feat_importance) - 1 - counter]] for j in range(len(X))]
                plt.scatter(sc, Y, c="b", alpha=0.5)
                plt.xlabel(sorted_name[counter])
                plt.ylabel(data_users[1][i])
                plt.title("Scatter plot for " + sorted_name[counter], fontsize=8)
                plt.legend(loc=2)
                plt.grid(True)
                counter += 1

            models.append(regr)
    plt.show()
    return models

def cross_validation_test(project):
    """
    Tests model with a leave-one-out cross validation method
    Outputs the scores associated to each model
    :param project: project name
    :return: None
    """
    data_users, X, name_X = load_data(project)
    nb = 1
    for i in range(len(data_users[0])):
        if data_users[0][i] == 'Y':
            Y = np.zeros(len(data_users) - 2)
            for j in range(len(data_users) - 2):
                Y[j] = np.float(data_users[j + 2][i])

            sample = np.arange(len(X))
            np.random.shuffle(sample)
            regr = ExtraTreesRegressor(bootstrap=False, criterion='mse', max_depth=None,
                                  max_features='auto', max_leaf_nodes=None,
                                  min_impurity_decrease=0.0, min_impurity_split=None,
                                  min_samples_leaf=1, min_samples_split=2,
                                  min_weight_fraction_leaf=0.0, n_estimators=1000, n_jobs=1,
                                  oob_score=False, verbose=0, random_state=0, warm_start=False)
            avg_cv = 0
            #cv_scores = cross_val_score(regr, X, Y, cv=len(X),
            #                            scoring='neg_mean_absolute_error')
            cv_scores, pred_grades = leave_one_out_cv(regr, X, Y)

            for j in range(len(cv_scores)):
                cv_scores[j] = abs(cv_scores[j])
                avg_cv += cv_scores[j]
            avg_cv = avg_cv / len(cv_scores)

            plt.figure(nb)
            nb += 1
            plt.scatter(pred_grades, Y, c="b", alpha=0.5)
            plt.plot([0,20], [0,20], '-', c='r')
            plt.plot([2,20], [0,18], '-', c='g')
            plt.plot([0, 18], [2, 20], '-', c='g')
            plt.xlabel("Predicted Grades")
            plt.ylabel("Actual Grades")
            plt.title("Scatter plot for Comparing " + data_users[1][i])
            plt.legend(loc=2)
            plt.grid(True)

            plt.figure(nb)
            plt.scatter(np.arange(0, len(cv_scores)), cv_scores, c="b", alpha=0.5)
            plt.xlabel("Users")
            plt.ylabel("Error")
            plt.title("Error Scatter plot for " + data_users[1][i])
            plt.legend(loc=2)
            plt.grid(True)
            nb += 1

            cv_scores.sort()
            fig = plt.figure(nb)
            nb += 1
            ax = fig.add_subplot(111)
            ax.boxplot(cv_scores)
            ax.set_xlabel('Data Points')
            ax.set_ylabel('Error')
            plt.grid(True)
            plt.title("Error rate for " + data_users[1][i])

            print "AVG score for " + data_users[1][i] + ": " + str(avg_cv)
            print "MEDIAN score for " + data_users[1][i] + ": " + str(cv_scores[int(len(cv_scores)/2)])

            regr = ExtraTreesRegressor(bootstrap=False, criterion='mse', max_depth=None,
                                       max_features='auto', max_leaf_nodes=None,
                                       min_impurity_decrease=0.0, min_impurity_split=None,
                                       min_samples_leaf=1, min_samples_split=2,
                                       min_weight_fraction_leaf=0.0, n_estimators=1000, n_jobs=1,
                                       oob_score=False, verbose=0, random_state=0, warm_start=False)
            regr.fit(X, Y)
            feat_importance = regr.feature_importances_
            sorted_args = np.argsort(feat_importance)
            sorted_name = [name_X[sorted_args[len(feat_importance) - j - 1]] for j in range(len(feat_importance))]



    plt.show()


if __name__ == '__main__':

    if len(sys.argv) != 3:
        print "Format : python data_learning.py <project_name> <mode>"
        print "  <mode> := 'MODEL' | 'CV' | 'PREDICT'"
    else:
        project = sys.argv[1]
        mode = sys.argv[2]
        if mode == 'MODEL':
            models = build_models(project)
        elif mode == 'CV':
            models = cross_validation_test(project)




""""
# Generate X and Y
#X = np.zeros((len(data_users), len(data_users[0]) - 6))
#Y = np.zeros(len(data_users))
#for i in range(0, len(data_users)):
#    u = data_users[i]
#    for j in range(0, len(u) - 6):
#        X[i][j] = np.float(u[j + 4])
#    Y[i] = np.float(u[len(u) - 1])


# To suffle our data set
sample = np.arange(len(X))
np.random.shuffle(sample)

# Use a random forest Regressor
# 2.303
regr = ExtraTreesRegressor(bootstrap=False, criterion='mse', max_depth=None,
                      max_features='auto', max_leaf_nodes=None,
                      min_impurity_decrease=0.0, min_impurity_split=None,
                      min_samples_leaf=1, min_samples_split=2,
                      min_weight_fraction_leaf=0.0, n_estimators=1000, n_jobs=1,
                      oob_score=False, random_state=0, verbose=0, warm_start=False)

#regr = AdaBoostRegressor(DecisionTreeRegressor(max_depth=20), n_estimators=100, random_state=np.random.RandomState(1))
# score 2.417

#regr = BaggingRegressor(DecisionTreeRegressor(max_depth=20), n_estimators=100, random_state=np.random.RandomState(1))
# score 2.308

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
vars = [ann[i+4] for i in range(len(feat))]
feat.append(0.0)
vars.append("")
plt.xticks(x_tics, vars, rotation=90)
plt.subplots_adjust(bottom=0.3)
plt.hist(x_tics, bins=x_tics, align='left', weights=feat, rwidth=0.4)
plt.grid(True)
plt.show()
"""""
