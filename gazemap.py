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

# Credits to PyGazeAnalyser (https://github.com/esdalmaijer/PyGazeAnalyser)
# Heavily adapted their code for our use case.

__author__ = "Vanhee Laurent <laurent.vanhee@student.uliege.ac.be>"
__copyright__ = "Copyright 2010-2017 University of Liège, Belgium, http://www.cytomine.be/"


from PIL import Image, ImageDraw
import csv
import os
from ast import literal_eval
import numpy as np
import config
from matplotlib import pyplot, image as matImage
from sklearn import cluster
from pygazeanalyser.gazeplotter import make_heatmap
import config

STD = 6
RATIO = 1.0
COLORS = {"green": ['#8ae234',
                      '#73d216',
                      '#4e9a06'],
        "aluminium": ['#eeeeec',
                      '#d3d7cf',
                      '#babdb6',
                      '#888a85',
                      '#555753',
                      '#2e3436'],
        }

class ImageGaze:
    # used for testing heatmap library
    def __init__(self, image_dir):

        self.image_dir = image_dir
        self.image = Image.open(image_dir)

    def user_gaze(self, csv_dir, output_dir):
        radius = 10

        file = open(csv_dir, 'rb')
        csvin = csv.reader(file)
        data = list(csvin)
        data.pop(0)
        file.close()

        file = open("tmp.csv", 'wb')
        csvout = csv.writer(file)
        for row in data:
            data = literal_eval(row[1])
            x,y = data
            csvout.writerow([round(y),round(x),row[2]])

        file.close()

        rescaled_width, rescaled_height = self.image.size

        # Create output heatmap file
        # Set range to constrained heatmap coordinates (resized image size)
        range = "0,0," + str(rescaled_height) + "," + str(rescaled_width)
        # print range
            # We use heatmap.py (AGPL) to be downloaded from https://github.com/sethoscope/heatmap
        # Create command line from arguments and launch heatmap code for image (and video)
        # e.g. python heatmap.py -b white -I cytomine-thumb.png -e 0,0,853,1024 -r 20 -P equirectangular -a --frequency 1 -o output.mpeg cytomine-positions.csv
        # gradient file geenrated e.g. using convert -size 256x256 gradient:DarkGreen-yellow PNG32:linear_gradient.png
        command_line = "heatmap.py" + " -v -b " + "white" + " -I " + self.image_dir + " -e " + range + " -r " + str(
            radius) + " -P " + "equirectangular " + " -G linear_gradient.png "
        command_line_img = command_line + "-o " + output_dir + " " + "tmp.csv"
        print command_line_img
        os.system('python ' + command_line_img)

        os.remove("tmp.csv")


def get_dimensions(corners):
    """
    Get the dimension of a position based on the distance of its corners.
    This is used to determine the feild of view of a zoom
    :param corners: list containing 4 points with (x,y) values
    :return: (x,y) dimension of the position
    """
    x0, y0 = corners[0]
    x1, y1 = corners[1]
    x2, y2 = corners[2]
    x3, y3 = corners[3]

    x = max([abs(x0 - x1), abs(x0 - x2), abs(x0 - x3)])
    y = max([abs(y0 - y1), abs(y0 - y2), abs(y0 - y3)])
    return x, y



def cluster_points(points, duration=20):
    """
    Clusters a set of points for the generation of a scanpath,
    We cluster  (k means) so that in the end, we have a maximum of 30 points so that
    the scanpath can be viewable
    :param points: dictionary of positions with at least 'x', 'y', and 'timestamp' fields
    :param duration: duration value forced on each point (we assume each position has the same duration in this case)
    :return: a new dictionary of positions with 'x', 'y', 'dur', and 'timestamp' fields
    """
    TIME_VAL = 100000

    # set the size of the cluster
    nb = min(config.CLUSTER_SIZE, len(points['x'])/10)
    if nb == 0:
        return points

    k_means = cluster.KMeans(n_clusters=int(nb), precompute_distances=True)

    X = np.zeros([len(points['x']), 3])

    # fit data into a np 2D array (tweakabale)
    for i in range(len(points['x'])):
        X[i][0] = points['x'][i]
        X[i][1] = points['y'][i]
        X[i][2] = points['timestamp'][i]/TIME_VAL

    # apply clustering
    k_means.fit(X)

    # get the new positions and the labels for the old positions
    centers = k_means.cluster_centers_
    labels = k_means.labels_

    # determine size of each cluster
    cluster_size = np.zeros(len(centers))
    for i in range(len(labels)):
        cluster_size[labels[i]] += 1

    # sort clusters by timestamp
    cluster_size = cluster_size[np.argsort(centers[:, 2])]
    centers = centers[np.argsort(centers[:, 2])]

    # put all the new data into the output dictionary
    ret = {'x': np.zeros(len(centers)),
           'y': np.zeros(len(centers)),
           'timestamp': np.zeros(len(centers)),
           'dur': np.zeros(len(centers))}
    for i in range(len(centers)):
        ret['x'][i] = centers[i][0]
        ret['y'][i] = centers[i][1]
        ret['timestamp'][i] = centers[i][2]*TIME_VAL
        ret['dur'][i] = cluster_size[i] * duration

    return ret

# todo finish, atm threshold is set at 100
def score_user_on_image(user_positions, annotation_actions, image_data):
    """
    Guesses a score for each user when it comes to viewing an image (from 0 to 1, or -1 if image not opened).
    The guessing is based on whether or not the user has clicked on annotations and heatmap values at the annotations' postions
    :param user_positions: dictionary of user positions
    :param annotation_actions: dictionary of annotation actions
    :param image_data: Image_Data object for particular image
    :return: user score
    """

    # unopened image
    if user_positions is None or len(user_positions['x']) == 0:
        return -1

    THRESHOLD = 100

    annotations = image_data.ref_annotations
    score = 0.0
    gazemap = None
    # If there are annotations in the image
    if annotations is not None:
        #for each annotation, check if there is an action
        for i in range(len(annotations['x'])):
            id = annotations['id'][i]
            x = annotations['x'][i]
            y = annotations['y'][i]
            visited = False
            if annotation_actions is not None:
                for j in range(len(annotation_actions['id'])):
                    if annotation_actions['id'][j] == id:
                        visited = True
                        break
            # if there is an action
            if visited:
                score += 1.0
            # otherwise check heatmap
            else:
                if gazemap is None:
                    gazemap = make_heatmap(user_positions, (image_data.rescaled_width, image_data.rescaled_height), image_data)

                heat = gazemap[int(y)][int(x)]
                if heat > THRESHOLD:
                    score += 1.0
                else:
                    score += heat/float(THRESHOLD) # it's regressive, maybe better results if we don't add to score if under threshold
        return score / float(len(annotations['x']))
    # If there are no annotations, just score based on the viewing of the entire image
    else:
        gazemap = make_heatmap(user_positions, (image_data.rescaled_width, image_data.rescaled_height), image_data)
        avg = np.mean(gazemap)
        if avg > THRESHOLD:
            score += 1.0
        else:
            score += avg/THRESHOLD
        return score


## test
if __name__ == '__main__':
    i = ImageGaze(config.WORKING_DIRECTORY + "gold/images/image_1217722/image.png")

    #i.user_gaze(config.WORKING_DIRECTORY + "gold/images/image_1217722/user_positions/1756092_s155297_cytomine_positions.csv",
    #            config.WORKING_DIRECTORY + "gold/images/image_1217722/test.png")

    #i.user_gaze(config.WORKING_DIRECTORY + "gold/images/image_1217722/user_positions/5861452_kZit_cytomine_positions.csv",
    #            config.WORKING_DIRECTORY + "gold/images/image_1217722/test2.png")

    result = 0.0
    t = 0.95
    temp = 1
    for i in range(0, 100):
        result += temp
        temp = temp*t
    print result
    print t