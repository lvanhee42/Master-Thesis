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
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import sys
from matplotlib.patches import Rectangle
from sklearn.linear_model import lasso_path
from itertools import cycle
from scipy.stats.stats import pearsonr
import Tkinter as tk
from Tkinter import *
import tkMessageBox
from multiprocessing import Process, Lock
import thread
from PIL import ImageTk, Image
from tkinter.filedialog import askdirectory
import datetime
import os
import subprocess
import time
import Queue

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


    # count the number of X variables to allocate np array
    l_x = 0
    for i in range(len(data_users[0])):
        if data_users[0][i] == 'X':
            l_x += 1
    name_X = []
    X = np.zeros((len(data_users) - 2, l_x))
    Y_list = []
    Y_name = []
    # fill the numpy array with variables
    j = 0
    for i in range(0, len(data_users[0])):
        if data_users[0][i] == 'X':
            name_X.append(data_users[1][i])
            for k in range(0, len(data_users) - 2):
                try:
                    X[k][j] = np.float(data_users[k + 2][i])
                except:
                    X[k][j] = np.float(data_users[k + 2][i].replace('+AC0', ''))
            j += 1
        if data_users[0][i] == 'Y':
            Y = np.zeros(len(data_users) - 2)
            Y_name.append(data_users[1][i])
            for k in range(0, len(data_users) - 2):
                try:
                    Y[k] = np.float(float(data_users[k + 2][i]))
                except:
                    Y[k] = np.float(float(data_users[k + 2][i].replace('+AC0', '')))
            Y_list.append(Y)
    return data_users, X, name_X, Y_list, Y_name

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

def median_out_error(Y):
    """
    Does a leave one out cross validation of the median model
    calculates the the Mean absolute error of the median model
    :param Y: Y variable
    :return: MAE, values predicted
    """
    error = 0
    vals = []
    for i in range(len(Y)):
        avg = []
        for j in range(len(Y)):
            if i != j:
                avg.append(Y[j])
        avg.sort()
        error += abs(avg[int(len(avg)/2)] - Y[i])
        vals.append(avg[int(len(avg)/2)])

    ret = error/len(Y)
    return ret, vals



def build_models(project, index=None, savedir=config.WORKING_DIRECTORY):
    """
    Builds a FULL model from all the users in the learning file
    This is done for every Y variable (EG practical/theoretical results) or a specific variable if defined by the index
    Outputs a figure showing the variable importance for every Y variable
    :param project: project name
    :param index : the index of the Y variable used for learning
    :param savedir: the save directory where the statistics will be stored.
    :return: list of containers with a container :  A : type ('MD') for model
                                                    B : container: 1) the built ExtraTrees Regressor
                                                                   2) names of all the features
                                                                   3) the save directory
                                                                   4) the 2D array of features
                                                                   5) the array of output variables
                                                                   6) lasso alpha values
                                                                   7) lasso coefficients
                                                                   8) the name of the project
        """
    models = []
    data_users, X, name_X, y_list, y_name = load_data(project)
    print len(name_X)
    for i in range(len(y_list)):
        if index is None or i == index:
            Y = y_list[i]

            newX = np.copy(X)
            newY = np.copy(Y)
            j = 0
            while j < len(newY):
                if newY[j] < 0.1:
                    newX = np.delete(newX, j, 0)
                    newY = np.delete(newY, j, 0)
                else:
                    j += 1

            regr = ExtraTreesRegressor(bootstrap=False, criterion='mse', max_depth=None,
                                  max_features='auto', max_leaf_nodes=None,
                                  min_impurity_decrease=0.0, min_impurity_split=None,
                                  min_samples_leaf=10, min_samples_split=2,
                                  min_weight_fraction_leaf=0.0, n_estimators=10000, n_jobs=1,
                                  oob_score=False, random_state=0, verbose=0, warm_start=False)

            # fill FULL data set
            regr.fit(newX, newY)
            alphas_lasso, coefs_lasso, _ = lasso_path(newX, newY, 5e-12, fit_intercept=False)

            models.append(('MD', (regr, name_X, y_name[i], savedir, newX, newY, alphas_lasso, coefs_lasso, project)))

    return models

def model_graphs(data):
    """
    Takes the output of the learned data and models the graph
    :param data: container with : 1) built ExtraTree Regressor
                                  2) names of all the features
                                  3) the save directory
                                  4) the 2D array of features
                                  5) the array of output variables
                                  6) lasso alpha values
                                  7) lasso coefficients
                                  8) the name of the project

    :return: filedires : list of the directories of the files saved.
    """
    regr, name_X, y_name, savedir, newX, newY, alphas_lasso, coefs_lasso, project_name = data
    filedirs = []
    feat_importance = regr.feature_importances_
    sorted_args = np.argsort(feat_importance)
    sorted_feat = [feat_importance[sorted_args[len(feat_importance) - j - 1]] for j in range(len(feat_importance))]
    sorted_name = [name_X[sorted_args[len(feat_importance) - j - 1]] for j in range(len(feat_importance))]


    plot_size = min(80, len(sorted_feat))
    x_tics = [j for j in range(len(sorted_feat) + 1)]
    x_tics = x_tics[0:plot_size + 1]
    sorted_name = sorted_name[0:plot_size]
    sorted_feat = sorted_feat[0:plot_size]
    # plot feature importance
    plt.figure(figsize=(36, 20), dpi=80, facecolor='w', edgecolor='k')

    plt.ylabel("Variable Importance", fontsize=16)
    plt.xlabel("Variable", fontsize=16)
    plt.title("Importance of Variables used in ML for " + y_name, fontsize=20)

    sorted_feat.append(0.0)
    sorted_name.append("")
    plt.xticks(x_tics, sorted_name, rotation=90, fontsize=14)
    plt.subplots_adjust(bottom=0.3)
    _, _, bars = plt.hist(x_tics, bins=x_tics, align='left', weights=sorted_feat, rwidth=0.4)

    for j in range(0, len(bars)):
        n = sorted_name[j]
        sp = n.split(" ")
        if "DURING MODULE" in n:
            bars[j].set_fc('r')
        elif "AT IMAGE" in n:
            bars[j].set_fc('g')
        else:
            bars[j].set_fc('b')

    # create legend
    handles = [Rectangle((0, 0), 1, 1, color=c, ec="k") for c in ['r', 'g', 'b']]
    labels = ["Module vars", "Regular Image vars", "General vars"]
    plt.legend(handles, labels, fontsize=14)
    plt.grid(True)
    plt.subplots_adjust(left=None, bottom=0.42, right=None, top=0.95,
                        wspace=None, hspace=None)
    fname = savedir + "var_importance_" + y_name + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + ".png"
    filedirs.append(fname)

    plt.savefig(fname)

    plt.figure(figsize=(36, 20), dpi=80, facecolor='w', edgecolor='k')

    counter = 0
    c = 230
    plt.suptitle("Variable Correlations for " + y_name, fontsize=20)
    for a in range(6):
        c += 1
        plt.subplot(c)
        sc = [newX[j][sorted_args[len(feat_importance) - 1 - counter]] for j in range(len(newX))]
        plt.scatter(sc, newY, c="b", alpha=0.5)
        plt.xlabel(sorted_name[counter], fontsize=16)
        plt.ylabel(y_name, fontsize=16)
        plt.plot(sc, np.poly1d(np.polyfit(sc, newY, 1))(sc), c='r')
        plt.title(sorted_name[counter], fontsize=20)
        plt.legend(loc=2)
        pear = pearsonr(sc, newY)[0]
        handles = [Rectangle((0, 0), 1, 1, color=co, ec="k") for co in ['r']]
        pear_st = "%.2f" % pear
        labels = ["Pearson Correlation of " + pear_st]
        plt.legend(handles, labels, fontsize=18)
        plt.grid(True)
        counter += 1

    fname = savedir + "var_correlation_" + y_name + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + ".png"
    filedirs.append(fname)
    plt.savefig(fname)

    plt.figure(figsize=(36, 20), dpi=80, facecolor='w', edgecolor='k')

    handles = []
    labels = []
    sorted_lasso = [coefs_lasso[sorted_args[len(feat_importance) - j - 1]] for j in range(len(feat_importance))]
    colors = ['b', 'c', 'g', 'y', 'r']
    lines_st = ['solid', 'dashed', 'dashdot', 'dotted']
    neg_log_alphas_lasso = -np.log10(alphas_lasso)
    cnt = 0
    ccnt = 0
    linescnt = 0
    for lass in range(20):
        c = colors[ccnt]
        lin = lines_st[linescnt]
        linescnt += 1
        if linescnt >= len(lines_st):
            ccnt += 1
            linescnt = 0
        line, = plt.plot(neg_log_alphas_lasso, sorted_lasso[lass], c=c, linestyle=lin)
        handles.append(line)
        labels.append(sorted_name[lass])

    plt.legend(handles, labels, loc=2, fontsize=16)
    plt.xlabel('-Log(alpha)', fontsize=16)
    plt.ylabel('coefficients', fontsize=16)
    plt.title('Lasso for ' + y_name, fontsize=20)
    plt.axis('tight')
    fname = savedir + "var_lasso_" + y_name + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + ".png"
    filedirs.append(fname)
    plt.savefig(fname)

    images = os.listdir(config.WORKING_DIRECTORY + project_name + "/images/")
    for i in range(len(images)):
        images[i] = images[i].split('_')[1]


    weights = []
    for i in range(len(images)):
        w = 0.0
        nb = 0
        for j in range(len(name_X)):
            if images[i] in name_X[j]:
                w = w + feat_importance[j]
                nb = nb + 1
        if nb == 0:
            weights.append(0)
        else:
            weights.append(w/nb)
    sorted_args = np.argsort(weights)
    sorted_feat = [weights[sorted_args[len(weights) - j - 1]] for j in range(len(weights))]
    sorted_name = [images[sorted_args[len(images) - j - 1]] for j in range(len(images))]

    modules = get_modules(project_name)
    modules_colors = ['#1f77b4', 'r', 'b', 'g', 'c', 'm', 'y', 'k']

    plot_size = len(sorted_name)
    x_tics = [j for j in range(len(sorted_feat) + 1)]
    x_tics = x_tics[0:plot_size + 1]
    sorted_name = sorted_name[0:plot_size]
    sorted_feat = sorted_feat[0:plot_size]
    # plot feature importance
    plt.figure(figsize=(36, 20), dpi=80, facecolor='w', edgecolor='k')

    plt.ylabel("Image Importance", fontsize=16)
    plt.xlabel("Image ID", fontsize=16)
    plt.title("Average Importance of the Images used in ML for " + y_name, fontsize=20)

    sorted_feat.append(0.0)
    sorted_name.append("")
    plt.xticks(x_tics, sorted_name, rotation=90, fontsize=14)
    plt.subplots_adjust(bottom=0.3)
    _, _, bars = plt.hist(x_tics, bins=x_tics, align='left', weights=sorted_feat, rwidth=0.4)

    for j in range(0, len(bars)):
        n = sorted_name[j]
        bars[j].set_fc(modules_colors[0])
        for i in range(len(modules)):
            im_mod = modules[i]
            if n in im_mod:
                bars[j].set_fc(modules_colors[i + 1])
                break

    # create legend
    handles = [Rectangle((0, 0), 1, 1, color=modules_colors[c + 1], ec="k") for c in range(len(modules))]
    handles.append(Rectangle((0, 0), 1, 1, color=modules_colors[0], ec="k"))
    labels = ["Module " + str(c + 1) for c in range(len(modules))]
    labels.append("No module")
    plt.legend(handles, labels, fontsize=14)
    plt.grid(True)

    fname = savedir + "im_importance_" + y_name + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + ".png"
    filedirs.append(fname)
    plt.savefig(fname)




    plt.close('all')

    return filedirs

def cross_validation_test(project, index=None, savedir=config.WORKING_DIRECTORY):
    """
    Tests model with a leave-one-out cross validation method
    Outputs the scores associated to each model unless a specific index is specified
    :param project: project name
    :param index : the index of the Y variable used for learning
    :param savedir: the save directory where the statistics will be stored.
    :return: list of containers with a container :  A : type ('CV') for cross validation
                                                    B : container: 1) CV scores
                                                                   2) predicted grades
                                                                   3) output variable vector
                                                                   4) name of the output variable vector
                                                                   5) save directory
        """
    models = []
    data_users, X, name_X, y_list, y_name = load_data(project)


    for i in range(len(y_list)):
        if index is None or i == index:
            Y = y_list[i]

            newX = np.copy(X)
            newY = np.copy(Y)
            j = 0
            while j < len(newY):
                if newY[j] < 0.1:
                    newX = np.delete(newX, j, 0)
                    newY = np.delete(newY, j, 0)
                else:
                    j += 1

            sample = np.arange(len(X))
            np.random.shuffle(sample)


            regr = ExtraTreesRegressor(bootstrap=False, criterion='mse', max_depth=None,
                                  max_features='auto', max_leaf_nodes=None,
                                  min_impurity_decrease=0.0, min_impurity_split=None,
                                  min_samples_leaf=10, min_samples_split=2,
                                  min_weight_fraction_leaf=0.0, n_estimators=1000, n_jobs=1,
                                  oob_score=False, verbose=0, random_state=0, warm_start=False)

            cv_scores, pred_grades = leave_one_out_cv(regr, newX, newY)

            models.append(('CV', (cv_scores, pred_grades, newY, y_name[i], savedir)))


    return models


def cv_graphs(data):
    """
    Takes the output of the learned data and models the graph
    :param data: container with : 1) CV scores
                                  2) predicted grades
                                  3) output variable vector
                                  4) name of the output variable vector
                                  5) save directory

    :return: filedires : list of the directories of the files saved.
    """
    cv_scores, pred_grades, newY, y_name, savedir, = data
    filedirs = []
    avg_cv = 0
    for j in range(len(cv_scores)):
        cv_scores[j] = abs(cv_scores[j])
        avg_cv += cv_scores[j]
    avg_cv = avg_cv / len(cv_scores)

    med, arr = median_out_error(newY)
    arr = np.array(arr)
    from scipy import stats
    _, p = stats.ttest_ind(pred_grades, newY)
    _, p2 = stats.ttest_ind(newY, arr)



    plt.figure()
    plt.scatter(newY, pred_grades, c="b", alpha=0.5)
    plt.plot([0, 20], [0, 20], '-', c='r')
    plt.plot([avg_cv, 20], [0, 20-avg_cv], '-', c='g')
    plt.plot([0, 20-avg_cv], [avg_cv, 20], '-', c='g')
    plt.plot(newY, np.poly1d(np.polyfit(newY, pred_grades, 1))(newY), c='navy')
    plt.ylabel("Predicted Grades")
    plt.xlabel("Actual Grades")
    plt.title("Scatter plot for Comparing " + y_name)
    plt.legend(loc=2)
    plt.grid(True)
    handles = [Rectangle((0, 0), 1, 1, color='r', ec="k")]
    handles.append(Rectangle((0, 0), 1, 1, color='g', ec="k"))
    handles.append(Rectangle((0, 0), 1, 1, color='navy', ec="k"))
    pear = pearsonr(newY, pred_grades)[0]
    pear_st = "%.2f" % pear
    avg_str = "%.2f" % avg_cv
    labels = ["y = x"]
    labels.append("y = x +- " + avg_str + " (mean abs. error)")
    labels.append("Pearson Correlation of " + pear_st)
    plt.legend(handles, labels, fontsize=8)

    savefile = savedir + "cv_comp_" + y_name + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + ".png"
    filedirs.append(savefile)
    plt.savefig(savefile)

    plt.figure()

    plt.scatter(np.arange(0, len(cv_scores)), cv_scores, c="b", alpha=0.5)
    plt.xlabel("Users")
    plt.ylabel("Error")
    plt.title("Error Scatter plot for " + y_name)
    plt.legend(loc=2)
    plt.grid(True)
    savefile = savedir + "cv_error_" + y_name + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + ".png"
    filedirs.append(savefile)
    plt.savefig(savefile)

    cv_scores.sort()

    fig = plt.figure()

    ax = fig.add_subplot(111)
    ax.boxplot(cv_scores)
    ax.set_xlabel('Data Points')
    ax.set_ylabel('Error')
    plt.grid(True)
    plt.title("Error rate for " + y_name)
    savefile = savedir + "cv_boxplot_" + y_name + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + ".png"
    filedirs.append(savefile)
    plt.savefig(savefile)

    grades = newY.copy()
    grades.sort()

    pred_grades_tmp = pred_grades[:]
    pred_grades_tmp.sort()

    out_str = ""

    out_str += y_name + " " + datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + "\n\n"

    out_str += "AVG score : " + str(avg_cv) + "\n"
    out_str += "Error from Median Model : " + str(med) + "\n"
    out_str += "score difference to Median: " + str(med - avg_cv) + "\n"
    out_str += "MEDIAN Real Grade : " + str(grades[int(len(grades) / 2)]) + "\n"
    out_str += "MEDIAN Estimated Grade : " + str(pred_grades_tmp[int(len(pred_grades_tmp) / 2)]) + "\n"
    #out_str += "P Value : " + str(p) + "\n"
    #out_str += "P Value of Median model : " + str(p2) + "\n"
    savefile = savedir + "cv_stats_" + y_name + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + ".txt"

    with open(savefile, "w") as text_file:
        text_file.write(out_str)



    print out_str
    print ""
    plt.close('all')

    return filedirs


def get_modules(project):
    """
    Gets the images associated to each module
    :param project: project name
    :return: list of modules, in each module a list of images
    """
    dir_l = os.listdir(config.WORKING_DIRECTORY + project + "/")
    if "timeline.csv" not in dir_l:
        return []

    f = open(config.WORKING_DIRECTORY + project + "/timeline.csv", 'rb')
    csv_in = csv.reader(f)
    data = list(csv_in)
    modules = []
    for k in range(1, len(data)):
        row = data[k]
        i = 3
        images = []
        while i + 1 < len(row) and row[i] != "":
            im_id = row[i]
            images.append(im_id)
            i += 2
        modules.append(images)
    f.close()
    return modules

def run_model(gui, project, idx, lock, dir):
    """
    For multithreaded application using GUI this runs a model analysis
    :param gui: GUI object
    :param project: project name
    :param idx: output variable index
    :param lock: lock to shared variables
    :param dir: save file directory
    :return: None
    """

    #print "start"
    lock.acquire()
    gui.working += 1
    lock.release()
    data = build_models(project, idx, dir)

    lock.acquire()
    gui.working -= 1
    for d in data:
        gui.data_queue.append(d)
    lock.release()
    #print "done"
    exit()

def run_cv(gui, project, idx, lock, dir):
    """
    For multithreaded application using GUI this runs a cv analysis
    :param gui: GUI object
    :param project: project name
    :param idx: output variable index
    :param lock: lock to shared variables
    :param dir: save file directory
    :return: None
    """

    #print "start"
    lock.acquire()
    gui.working += 1
    lock.release()
    data = cross_validation_test(project, idx, dir)

    lock.acquire()
    gui.working -= 1
    for d in data:
        gui.data_queue.append(d)
    lock.release()
    #print "done"
    exit()


class Gui(tk.Frame):
    """
    This class encapsulates a GUI for easy usage of this tool, it provides the option to run a model or cross validation using multithreaded programming.
    """
    def __init__(self, project, parent=None):
        self.data_users, self.X, self.name_X, self.y_list, self.y_name = load_data(project)
        self.project = project
        self.working = 0
        self.lock = Lock()
        self.file_dirs = []
        self.files_index = 0
        self.file_directory = config.WORKING_DIRECTORY
        self.data_queue = []

        # GUI structure
        tk.Frame.__init__(self, parent)
        self.parent = parent
        height = 100
        width = 300
        self.image_panel = None
        self.winfo_toplevel().title("Cytomine - Data Analysis")

        self.f1 = Frame(parent)
        self.f1.grid(column=0, row=0, sticky=(N, S, E, W))  # added sticky

        self.panel = Frame(self.parent)
        self.panel.grid(column=1, row=0, sticky=(N, S, E, W))#, padx=800, pady=500)

        self.dir_text = Text(self.f1, height=2, width=16)
        self.dir_text.grid(column=0, row=0, sticky=(N, S, E, W))
        self.dir_text.insert(END, "Files saved in : \n" + self.file_directory)

        self.dir_button = Button(self.f1, text="Set Save File Directory", command=self.load_file, width=10)
        self.dir_button.grid(column=0, row=1, sticky=(N, S, E, W))

        self.open_dir_button = Button(self.f1, text="Go to File Directory", command=self.startfile, width=10)
        self.open_dir_button.grid(column=0, row=2, sticky=(N, S, E, W))

        self.f2_canvas = Canvas(self.f1, height=height, width=width)
        self.f2_canvas.grid(column=0, row=3, sticky=(N, S, E, W))


        self.scrollbar = Scrollbar(self.f2_canvas)
        self.scrollbar.pack(side=tk.RIGHT, fill=Y)
        self.listbox = Listbox(self.f2_canvas, yscrollcommand=self.scrollbar.set)

        for i in range(len(self.y_name)):
            self.listbox.insert(tk.END, self.y_name[i])
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH)
        self.listbox.place(height=height, relwidth=0.95)

        self.scrollbar.place(height=height, relwidth=0.05, relx=0.95)
        self.scrollbar.config(command=self.listbox.yview)


        self.model_button = Button(self.f1, text="Study Model", command=self.launch_model)
        self.model_button.grid(column=0, row=4, sticky=(N, S, E, W))

        self.cv_button = Button(self.f1, text="Cross Validation", command=self.launch_cv)
        self.cv_button.grid(column=0, row=5, sticky=(N, S, E, W))

        self.p_text = Text(self.f1, height=2, width=16)
        self.p_text.grid(column=0, row=6, sticky=(N, S, E, W))
        self.p_text.insert(END, "Number of Tasks Running : \n" + str(self.working) + " / 8")

        self.update_clock()

    def startfile(self):
        """
        Opens a file explorer to the savefile directory
        :return: None
        """
        try:
            os.startfile(self.file_directory)
        except:
            subprocess.Popen(['xdg-open', self.file_directory])


    def load_file(self):
        """
        rebuilds the file directory information widget after user input new directory
        :return: None
        """
        fname = askdirectory()
        if fname:
            try:
                fname += "/"
                self.file_directory = fname
                self.dir_text.pack_forget()
                self.dir_text.destroy()
                self.dir_text = Text(self.f1, height=2, width=16)
                self.dir_text.grid(column=0, row=0, sticky=(N, S, E, W))
                self.dir_text.insert(END, "Files saved in : \n" + self.file_directory)
            except:
                tkMessageBox.showinfo("Error", "Something went terribly wrong")
            return

    def launch_cv(self):
        """
        Launch a cross validation
        :return: None
        """
        self.launch_op(op='cv')

    def launch_model(self):
        """
        Launch Model
        :return: None
        """
        self.launch_op(op='model')

    def launch_op(self, op='model'):
        """
        Launches a thread with either a CV or a model.
        A maximum number of 8 threads can run at once.
        :param op: operation type
        :return: None
        """
        self.lock.acquire()


        if self.working >= 8:
            self.lock.release()
            tkMessageBox.showinfo("Error", "Limited to 8 Simultaneous Executions")
            return

        self.p_text.pack_forget()
        self.p_text.destroy()
        self.p_text = Text(self.f1, height=2, width=16)
        self.p_text.grid(column=0, row=6, sticky=(N, S, E, W))
        self.p_text.insert(END, "Number of Tasks Running : \n" + str(self.working + 1) + " / 8")

        self.lock.release()


        try:
            selection = self.listbox.get(self.listbox.curselection())
            sel_idx = 0
            for i in range(len(self.y_list)):
                if str(selection) == str(self.y_name[i]):
                    sel_idx = i

            #Process(target=run_model, args=(self, self.project, sel_idx, self.lock)).start()
            #thread.start_new_thread(run_model, (self, self.project, sel_idx, self.lock))
            if op == 'model':
                #Process(target=run_model, args=(self, self.project, sel_idx, self.lock, self.file_directory)).start()
                thread.start_new_thread(run_model, (self, self.project, sel_idx, self.lock, self.file_directory))
                #run_model(self, self.project, sel_idx, self.lock, self.file_directory)
            else:
                #Process(target=run_cv, args=(self, self.project, sel_idx, self.lock, self.file_directory)).start()
                thread.start_new_thread(run_cv, (self, self.project, sel_idx, self.lock, self.file_directory))
                #run_cv(self, self.project, sel_idx, self.lock, self.file_directory)


        except:
            tkMessageBox.showinfo("Error", "Please Select a variable")


    def show_left_image(self):
        """
        When user clicks on left arrow button, displays the previous image
        :return: None
        """
        self.lock.acquire()
        if self.files_index == 0:
            self.files_index = len(self.file_dirs) - 1
        else:
            self.files_index -= 1

        img_tmp = Image.open(self.file_dirs[self.files_index])
        self.lock.release()
        img_tmp = img_tmp.resize((1500, 1000), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(img_tmp)

        self.image_panel.pack_forget()
        self.image_panel.destroy()
        self.image_panel = Label(self.panel, image=img)
        self.image_panel.image = img
        self.image_panel.grid(column=0, row=0, sticky=(N, S, E, W))

        self.model_text.pack_forget()
        self.model_text.destroy()
        self.model_text = Text(self.arrow_buttons, height=2, width=5)
        self.model_text.grid(column=1, row=0, sticky=(N, S, E, W))
        self.model_text.insert(END, str(self.files_index + 1) + "/" + str(len(self.file_dirs)))


    def show_right_image(self):
        """
        When user clicks on right arrow button, displays next image
        :return: None
        """
        self.lock.acquire()
        if self.files_index == len(self.file_dirs) - 1:
            self.files_index = 0
        else:
            self.files_index += 1

        img_tmp = Image.open(self.file_dirs[self.files_index])
        self.lock.release()
        img_tmp = img_tmp.resize((1500, 1000), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(img_tmp)

        self.image_panel.pack_forget()
        tmp = self.image_panel.image
        del tmp
        self.image_panel.destroy()
        self.image_panel = Label(self.panel, image=img)
        self.image_panel.image = img
        self.image_panel.grid(column=0, row=0, sticky=(N, S, E, W))

        self.model_text.pack_forget()
        self.model_text.destroy()
        self.model_text = Text(self.arrow_buttons, height=2, width=5)
        self.model_text.grid(column=1, row=0, sticky=(N, S, E, W))
        self.model_text.insert(END, str(self.files_index + 1) + "/" + str(len(self.file_dirs)))


    def update_clock(self):
        """
        At every clock cycle, checks if there are no updates in the model.
        If the CV or models are finished, it launches the methods to display the statistics.
        Also keeps info about the directories to display as images.
        :return: None
        """
        self.lock.acquire()
        if len(self.file_dirs) > 0 and self.image_panel is None:
            img_tmp = Image.open(self.file_dirs[self.files_index])
            img_tmp = img_tmp.resize((1500, 1000), Image.ANTIALIAS)
            img = ImageTk.PhotoImage(img_tmp)
            self.image_panel = Label(self.panel, image=img)
            self.image_panel.image = img
            self.image_panel.grid(column=0, row=0, sticky=(N, S, E, W))

            self.arrow_buttons = Frame(self.panel)
            self.arrow_buttons.grid(column=0, row=1, sticky=(N, S, E, W))

            self.model_left_button = Button(self.arrow_buttons, text="<=", command=self.show_left_image)
            self.model_left_button.grid(column=0, row=0, sticky=(N, S, E, W))

            self.model_text = Text(self.arrow_buttons, height=2, width=5)
            self.model_text.grid(column=1, row=0, sticky=(N, S, E, W))
            self.model_text.insert(END, str(self.files_index + 1) + "/" + str(len(self.file_dirs)))

            self.model_right_button = Button(self.arrow_buttons, text="=>", command=self.show_right_image)
            self.model_right_button.grid(column=2, row=0, sticky=(N, S, E, W))

        while len(self.data_queue) > 0:

            data = self.data_queue.pop(0)
            tmp1, tmp2 = data
            if tmp1 == 'MD':
                self.file_dirs += model_graphs(tmp2)
            else:
                self.file_dirs += cv_graphs(tmp2)

            if len(self.data_queue) == 0 and self.image_panel is not None:
                self.model_text.pack_forget()
                self.model_text.destroy()
                self.model_text = Text(self.arrow_buttons, height=2, width=5)
                self.model_text.grid(column=1, row=0, sticky=(N, S, E, W))
                self.model_text.insert(END, str(self.files_index + 1) + "/" + str(len(self.file_dirs)))

            self.p_text.pack_forget()
            self.p_text.destroy()
            self.p_text = Text(self.f1, height=2, width=16)
            self.p_text.grid(column=0, row=6, sticky=(N, S, E, W))
            self.p_text.insert(END, "Number of Tasks Running : \n" + str(self.working) + " / 8")

        self.lock.release()
        self.parent.after(1000, self.update_clock)

if __name__ == '__main__':

    if len(sys.argv) == 3:
        project = sys.argv[1]

        dir_l = os.listdir(config.WORKING_DIRECTORY)
        if project not in dir_l:
            print "Error: Project does not already exist"
            exit()

        dir_l = os.listdir(config.WORKING_DIRECTORY + project + "/")
        if "learning_data.csv" not in dir_l:
            print "Error: learning_data file does not exist in project " + project
            exit()

        mode = sys.argv[2]
        if mode == 'MODEL':
            models = build_models(project)
            for model in models:
                _, tmp = model
                model_graphs(tmp)
        elif mode == 'CV':
            models = cross_validation_test(project)
            for model in models:
                _, tmp = model
                cv_graphs(tmp)
        else:
            root = tk.Tk()
            gui = Gui(project, parent=root)
            root.mainloop()
    elif len(sys.argv) == 4:
        project = sys.argv[1]
        mode = sys.argv[2]
        index = int(sys.argv[3])
        if mode == 'MODEL':
            models = build_models(project, index=index)
            for model in models:
                _, tmp = model
                model_graphs(tmp)
        elif mode == 'CV':
            models = cross_validation_test(project, index=index)
            for model in models:
                _, tmp = model
                cv_graphs(tmp)
        else:
            print "Format : python data_learning.py <project_name> <mode> (<index>)"
            print "  <mode> := 'MODEL' | 'CV' | 'GUI'"
            print "  <index> := [0 - NbYvars[, the index of the Y var to do the study on"
    else:
        print "Format : python data_learning.py <project_name> <mode> (<index>)"
        print "  <mode> := 'MODEL' | 'CV' | 'GUI'"
        print "  <index> := [0 - NbYvars[, the index of the Y var to do the study on"



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
