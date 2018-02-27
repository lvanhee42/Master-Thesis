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


from ast import literal_eval
import numpy as np

from gazemap import RATIO, STD
from pygazeanalyser.gazeplotter import gaussian


def get_dimensions(corners):
    """
    Gets the dimension of a position based on the 4 corners of a position
    :param corners: list with 4 elements containg pairs of xy coordinates
    :return: (x_length, y_length)
    """
    x0, y0 = corners[0]
    x1, y1 = corners[1]
    x2, y2 = corners[2]
    x3, y3 = corners[3]

    x = max([abs(x0 - x1), abs(x0 - x2), abs(x0 - x3)])
    y = max([abs(y0 - y1), abs(y0 - y2), abs(y0 - y3)])
    return x, y


def get_nearest_annotation(timestamp, positions, annotations):
    """
    For a given timestamp (associated by a AnnotationAction),
    tries to guess which annotation was clicked on by the user (since it wasn't tracked)
    :param timestamp: timestamp of AnnotationAction
    :param positions: position of all the users in the image
    :param annotations: list of annotations in the image
    :return: annotation id (0 if still unknown)
    """

    # go through the positions and finds the closest position timestamp
    position_timestamps = positions['timestamp']
    index = len(position_timestamps) - 1
    for i in range(len(position_timestamps)):
        t = position_timestamps[i]
        if t >= timestamp and i > 0:
            prev = position_timestamps[i-1]
            if dist(prev, timestamp) < dist(t, timestamp):
                index = i - 1
            else:
                index = i
            break
        elif t >= timestamp and i == 0:
            index = 0
            break
    if index < 0:
        return 0

    # x, y coordinates of closest position
    x = positions['x'][index]
    y = positions['y'][index]

    d = np.inf
    ann_id = None
    # guess closest annotation
    for i in range(len(annotations['id'])):
        x_annot = annotations['x'][i]
        y_annot = annotations['y'][i]
        curr_dist = np.sqrt((dist(x, x_annot) ** 2) + (dist(y, y_annot) ** 2))
        if curr_dist < d:
            d = curr_dist
            ann_id = annotations['id'][i]

    return ann_id


def dist(a, b):
    """
    distance between 2 values
    :param a: val1
    :param b: val2
    :return: distance between a and b
    """
    return np.abs(b - a)


def parse_positions(data, image_data, duration=20, calc_gauss=True):
    """
    parse positions of a user in an image to a dictionary based on data read from file
    :param data: data directly read from position file
    :param image_data: ImageData object to store eventual gaussians
    :param duration: base duration for each position (updated later)
    :param calc_gauss: Whether or not gaussians are calculated for zoom levels
    :return: dictionary of positions
    """

    # dict template
    ret = {'x': np.zeros(len(data)),
           'y': np.zeros(len(data)),
           'dur': np.zeros(len(data)),
           'timestamp': np.zeros(len(data), dtype=np.double),
           'zoom': np.zeros(len(data),dtype=np.int64),
           'corners': [],
           'heatmap': None}

    # fills dictionary
    for row in range(len(data)):
        row_data = data[row]
        x, y = literal_eval(row_data[1])
        ret['x'][row] = x
        ret['y'][row] = y
        ret['dur'][row] = duration
        corners = literal_eval(row_data[0])
        ret['corners'].append(corners)
        ret['zoom'][row] = row_data[2]
        ret['timestamp'][row] = np.double(row_data[3])

        # calculate gaussian if needed
        if calc_gauss and ret['zoom'][row] > 3:
            if image_data.gaussians['zoom_' + str(row_data[2])] is None:
                x_l, y_l = get_dimensions(corners)
                zoom_x = max(1, RATIO * x_l)
                zoom_y = max(1, RATIO * y_l)
                sx = max(1, np.int(zoom_x / STD))
                sy = max(1, np.int(zoom_y / STD))
                d = (gaussian(np.int(zoom_x), sx, np.int(zoom_y), sy), zoom_x, zoom_y)
                image_data.gaussians['zoom_' + str(row_data[2])] = d
    return ret


def parse_annotations(data):
    """
    parse annotations of a user in an image to a dictionary based on data read from file
    :param data: data directly read from annotation files
    :return: dictionary of annotations
    """

    # dict template
    ret = {'x': np.zeros(len(data)),
           'y': np.zeros(len(data)),
           'id': np.zeros(len(data)),
           'type': []}

    # fills dictionary
    for row in range(len(data)):
        row_data = data[row]
        ret['x'][row] = row_data[1]
        ret['y'][row] = row_data[2]
        ret['id'][row] = row_data[3]
        ret['type'].append(row_data[0])

    return ret


def parse_annotation_actions(data, positions, annotations):
    """
    parse annotationActions of a user in an image to a dictionary based on data read from file
    :param data: data directly read from annotationActions files
    :param positions: dictionary of positions (associated to user/image pair)
    :param annotations: annotations associated to image
    :return: dictionary of AnnotationActions
    """

    # dict template
    ret = {'id' : np.zeros(len(data)),  # annotation id = 0 if it cannot be guessed
           'action' : [],
           'timestamp': np.zeros(len(data))}

    # fils dict
    for row in range(len(data)):
        row_data = data[row]

        # guesses id if id not in file
        if row_data[0] == "":
            ret['id'][row] = get_nearest_annotation(row_data[1], positions, annotations)
        else:
            ret['id'][row] = row_data[0]

        ret['action'].append(row_data[2])
        ret['timestamp'][row] = row_data[1]

    return ret
