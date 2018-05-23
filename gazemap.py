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
import matplotlib.pyplot as plt

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

def score_user_on_image(user_positions, annotation_actions, image_data, start_pos=0, end_pos=None, start_action=0, end_action=None):
    """
    Guesses a score for each user when it comes to viewing an image (from 0 to 1, or -1 if image not opened).
    The guessing is based on whether or not the user has clicked on annotations and heatmap values at the annotations' postions
    :param user_positions: dictionary of user positions
    :param annotation_actions: dictionary of annotation actions
    :param image_data: Image_Data object for particular image
    :param start_pos : the index of the first position
    :param end_pos : the index of the last position
    :param start_action : index of the first annotation action
    :param end_action : index of the last annotation action
    :return: user score
    """

    # unopened image
    if user_positions is None or len(user_positions['x']) == 0:
        return 0, None

    # check values of indexes if it's in our array
    if end_pos is None:
        end_pos = len(user_positions['x'])
    else:
        end_pos += 1

    if end_pos > len(user_positions['x']):
        end_pos = len(user_positions['x'])
    if start_pos < 0:
        start_pos = 0

    if annotation_actions is not None and end_action is None:
        end_action = len(annotation_actions['id'])
    elif annotation_actions is not None:
        end_action += 1

    if annotation_actions is not None and end_action > len(annotation_actions['id']):
        end_action = len(annotation_actions['id'])
    elif annotation_actions is not None and start_action < 0:
        start_action = 0

    THRESHOLD = 0.9*1/(1 - config.REDUCE_WEIGHT)

    annotations = image_data.ref_annotations
    score = 0.0
    gazemap = None
    # If there are annotations in the image
    if annotations is not None:
        k = 0
        gazemap = generate_reduced_heatmap_ann_scores(user_positions, image_data, annotations, start_pos, end_pos)
        #for each annotation, check if there is an action
        for i in range(len(annotations['x'])):
            id = annotations['id'][i]
            x = annotations['x'][i]
            y = annotations['y'][i]
            visited = False
            if annotation_actions is not None:
                for j in range(start_action, end_action):
                    if annotation_actions['id'][j] == id:
                        visited = True
                        break
            # if there is an action
            if visited:
                score += 1.0
            # otherwise check heatmap
            else:
                heat = gazemap[k]
                if heat > THRESHOLD:
                    score += 1.0
                else:
                    score += heat/float(THRESHOLD) # it's regressive, maybe better results if we don't add to score if under threshold
            k += 1

        return score / float(len(annotations['x'])), gazemap
    # If there are no annotations, just score based on the viewing of the entire image
    else:
        gazemap = generate_reduced_heatmap(user_positions, (image_data.rescaled_width, image_data.rescaled_height), image_data,
                                           start_pos=start_pos, end_pos=end_pos)
        avg = np.mean(gazemap)
        if avg > THRESHOLD:
            score += 1.0
        else:
            score += avg/THRESHOLD
        return score, None


def normalize(values, ratio=0.95):
    """
    calculates a normalized sum of a list of values
    uses a geometric sequence with a ratio of less than 1.
    :param values: unsorted list of values
    :param ratio: ratio of the normalizer
    :return: value
    """
    values.sort(reverse=True)
    weight = 1
    heat = 0
    for i in range(len(values)):
        heat += values[i]*weight
        weight *= ratio
    return heat


def generate_reduced_heatmap(fix, dispsize, image_data, start_pos=0, end_pos=None):
    """
    Generates a reduced heatmap
    :param fix: positions
    :param dispsize: size of the display
    :param image_data: Image_data object
    :param start_pos: index of the 1st position
    :param end_pos: index of the last position
    :return: 2D reduced heatmap array
    """
    three_def_vect = []
    zoom = float(image_data.zoom_max)
    for i in range(dispsize[1]):
        three_def_vect.append([])
        for j in range(dispsize[0]):
            three_def_vect[i].append([])

    if end_pos is None:
        end_pos = len(fix['dur'])

    for i in range(start_pos, end_pos):
        # get x and y coordinates
        if fix['zoom'][i] > 3:
            gaus, zoom_x, zoom_y = image_data.gaussians['zoom_' + str(fix['zoom'][i])]
            x = fix['x'][i] - np.int(zoom_x / 2)
            y = fix['y'][i] - np.int(zoom_y / 2)
            for k in range(np.int(zoom_y)):
                for l in range(np.int(zoom_x)):
                    coord_x = x + l
                    coord_y = y + k
                    if 0 <= coord_x < dispsize[0] and 0 <= coord_y < dispsize[1]:
                        three_def_vect[int(coord_y)][int(coord_x)].append(gaus[k][l]*(fix['zoom'][i]/zoom)) # * (fix['zoom'][i]/2.0))

    heatmap = np.zeros((dispsize[1], dispsize[0]), dtype=float)
    ratio = config.REDUCE_WEIGHT
    for i in range(dispsize[1]):
        for j in range(dispsize[0]):
            heatmap[i][j] = normalize(three_def_vect[i][j], ratio=ratio)


    heatmap[0][0] = 1 / (1 - ratio)
    return heatmap


def generate_reduced_heatmap_ann_scores(fix, image_data, annotations, start_pos, end_pos):
    """
    Similar to generating a reduced heatmap but only for specific pixels (IE locations of annotations)
    :param fix: positions
    :param image_data: Image_Data object
    :param annotations: reference annotations
    :param start_pos: index of the first position
    :param end_pos: index of the last position
    :return: list of scores for each annotation
    """
    scores = []
    zoom = float(image_data.zoom_max)
    for i in range(len(annotations['x'])):
        scores.append([])

    for i in range(start_pos, end_pos):
        # get x and y coordinates
        if fix['zoom'][i] > 3:
            gaus, zoom_x, zoom_y = image_data.gaussians['zoom_' + str(fix['zoom'][i])]
            x = fix['x'][i] - np.int(zoom_x / 2)
            y = fix['y'][i] - np.int(zoom_y / 2)

            for j in range(len(annotations['x'])):
                coord_x = annotations['x'][j] - x
                coord_y = annotations['y'][j] - y
                if 0 <= coord_x < zoom_x and 0 <= coord_y < zoom_y:
                    scores[j].append(gaus[int(coord_y)][int(coord_x)]*(fix['zoom'][i]/zoom))


    ret = []
    ratio = config.REDUCE_WEIGHT
    for i in range(len(scores)):
        ret.append(normalize(scores[i], ratio=ratio))

    return ret

def annotation_order(positions, annotations, id1, id2, gaussians, nb_pos, max_zoom):
    """
    Returns whether or not annotation 1 is visited before annotation 2
    :param positions: positions
    :param annotations: reference annotations
    :param id1: index of 1st annotation
    :param id2: index of 2nd annotation
    :param gaussians: dictionary of Gaussian 2D vectors
    :param nb_pos: Number of positions minimum to consider a annotation visited
    :param max_zoom: max zoom of an image
    :return:
    """

    idx2 = []
    ann2_x = annotations['x'][id2]
    ann2_y = annotations['y'][id2]

    idx1 = []
    ann1_x = annotations['x'][id1]
    ann1_y = annotations['y'][id1]

    # get 1st nb_pos positions for the first and second annotations
    for i in range(len(positions['x'])):

        zoom = positions['zoom'][i]
        x = positions['x'][i]
        y = positions['y'][i]
        if zoom > 3 and zoom > max_zoom - 5:
            gaus, zoom_x, zoom_y = gaussians['zoom_' + str(int(zoom))]

            if abs(x - ann2_x) <= zoom_x/2 and abs(y - ann2_y) <= zoom_y/2:
                idx2.append(i)

            if abs(x - ann1_x) <= zoom_x/2 and abs(y - ann1_y) <= zoom_y/2:
                idx1.append(i)

        if len(idx2) >= nb_pos and len(idx1) >= nb_pos:
            break

    # both were never visited, return 0 = false
    if len(idx1) == 0 and len(idx2) == 0:
            return 0
    # 1st was never visited, return 0 = false
    if len(idx1) == 0:
            return 0
    # 2nd was never visited, return 1 = true
    if len(idx2) == 0:
            return 1


    # get the average index for both vectors.
    avg1 = float(sum(idx1))/len(idx1)
    avg2 = float(sum(idx2))/len(idx2)


    if avg1 < avg2:
        return 1
    else:
        return 0





def study_heatmap(image_data):
    """
    Draws plots to compare different gaussians and their values.
    :param image_data:
    :return:
    """
    c = 330
    h = (np.arange(10) + 1)/10.0
    h = np.matrix(h)
    print h
    for i in range(6):
        c += 1
        plt.subplot(c)
        heatmap, _, _ = image_data.gaussians['zoom_' + str(i + 4)]
        heatmap = ((i+1)/6.0)*heatmap
        #heatmap[0][0] = 1
        plt.title("Gaussian for Zoom " + str(i + 4))
        plt.imshow(heatmap, cmap='jet', interpolation='nearest', vmax=1, vmin=0)
    plt.subplot(c + 2)
    #plt.axis('off')
    plt.yticks([])
    x_t = np.arange(10)
    x_tt = (np.arange(10) + 1)/10.0
    plt.xticks(x_t, x_tt)
    plt.imshow(h, cmap='jet', interpolation='nearest', vmax=1, vmin=0)
    plt.show()


## test
if __name__ == '__main__':

    generate_reduced_heatmap(None, [1024, 768], None)