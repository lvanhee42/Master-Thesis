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
from matplotlib import pyplot, image as matImage
from sklearn import cluster

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

def make_heatmap(fix, dispsize, image_data):

    gwh = 1024  # width in pixels (default 200)
    # matrix of zeroes
    strt = gwh / 2
    heatmapsize = dispsize[1] + 2 * strt, dispsize[0] + 2 * strt
    heatmap = np.zeros(heatmapsize, dtype=float)

    # create heatmap
    for i in range(0, len(fix['dur'])):
        # get x and y coordinates
        if fix['zoom'][i] > 3 :
            gaus, zoom_x, zoom_y = image_data.gaussians['zoom_' + str(fix['zoom'][i])]
            x = fix['x'][i] + strt - np.int(zoom_x / 2)
            y = fix['y'][i] + strt - np.int(zoom_y / 2)
            # correct Gaussian size if either coordinate falls outside of
            # display boundaries
            # add Gaussian to the current heatmap
            try:
                heatmap[np.int(y):np.int(y + zoom_y), np.int(x):np.int(x + zoom_x)] += gaus #* fix['zoom'][i]
            except:
                pass
    # resize heatmap
    heatmap = heatmap[strt:dispsize[1] + strt, strt:dispsize[0] + strt]
    return heatmap

def save_heatmap(heatmap, dispsize, imagefile, savefilename, alpha=0.5, avg=None):

    fig, ax = draw_display(dispsize, imagefile=imagefile)
    if len(heatmap[heatmap > 0]) > 0:
        if avg is None:
            lowbound = np.mean(heatmap[heatmap > 0])
        else:
            lowbound = avg
        heatmap[heatmap < lowbound] = np.NaN

        # draw heatmap on top of image
        ax.imshow(heatmap, cmap='jet', alpha=alpha)

    # FINISH PLOT
    # save the figure if a file name was provided
    fig.savefig(savefilename)
    fig.clf()
    pyplot.close("all")
    del ax
    del fig


def draw_raw(data, dispsize, imagefile=None, savefilename=None):
    # image
    fig, ax = draw_display(dispsize, imagefile=imagefile)

    ax.plot(data['x'], data['y'], 'o', color=COLORS['aluminium'][0],
            markeredgecolor=COLORS['aluminium'][5])

    if savefilename is not None:
        fig.savefig(savefilename)
    fig.clf()
    ax.clear()
    pyplot.close("all")
    del ax
    del fig


def draw_scanpath(fix, dispsize, imagefile, savefilename, alpha=0.5):
    # image
    fig, ax = draw_display(dispsize, imagefile=imagefile)

    # draw point with weights
    ax.scatter(fix['x'], fix['y'], s=fix['dur'], c=COLORS['green'][2],
               marker='o', cmap='jet', alpha=alpha,
               edgecolors='none')
    # draw points and order
    for i in range(len(fix['x'])):
        ax.annotate(str(i + 1), (fix['x'][i], fix['y'][i]),
                    color=COLORS['aluminium'][5], alpha=1,
                    horizontalalignment='center', verticalalignment='center',
                    multialignment='center')

    # draw arrows
    for i in range(len(fix['x']) - 1):
        ax.arrow(fix['x'][i], fix['y'][i], fix['x'][i + 1] - fix['x'][i], fix['y'][i + 1] - fix['y'][i], alpha=alpha,
                 fc=COLORS['aluminium'][0], ec=COLORS['aluminium'][5], fill=True,
                 shape='full', width=1, head_width=2,
                 head_starts_at_zero=False, overhang=0)

    fig.savefig(savefilename)

    fig.clf()
    pyplot.close("all")
    del ax
    del fig

def get_dimensions(corners):

    x0, y0 = corners[0]
    x1, y1 = corners[1]
    x2, y2 = corners[2]
    x3, y3 = corners[3]

    x = max([abs(x0 - x1), abs(x0 - x2), abs(x0 - x3)])
    y = max([abs(y0 - y1), abs(y0 - y2), abs(y0 - y3)])
    return x, y


def gaussian(x, sx, y=None, sy=None):
    if y is None:
        y = x
    if sy is None:
        sy = sx
    # centers
    xo = x / 2
    yo = y / 2
    # matrix of zeros
    M = np.zeros([y, x], dtype=float)
    # gaussian matrix
    for i in range(x):
        for j in range(y):
            M[j, i] = np.exp(-1.0 * (((float(i) - xo) ** 2 / (2 * sx * sx)) + ((float(j) - yo) ** 2 / (2 * sy * sy))))

    return M


def draw_display(dispsize, imagefile=None):

    # construct empty screen
    screen = np.zeros((dispsize[1], dispsize[0], 3), dtype='uint8')
    # if an image location has been passed, draw the image
    if imagefile != None:
        # check if the path to the image exists
        if not os.path.isfile(imagefile):
            raise Exception(
                "ERROR in draw_display: imagefile not found at " + str(imagefile))
        # load image
        img = matImage.imread(imagefile)
        if not os.name == 'nt':
            img = np.flipud(img)
        # width and height of the image
        w, h = len(img[0]), len(img)
        # x and y position of the image on the display
        x = dispsize[0] / 2 - w / 2
        y = dispsize[1] / 2 - h / 2
        # draw the image on the screen
        screen[y:y + h, x:x + w, :] += img
        del img

    # dots per inch
    dpi = 100.0
    # determine the figure size in inches
    figsize = (dispsize[0] / dpi, dispsize[1] / dpi)
    # create a figure
    fig = pyplot.figure(figsize=figsize, dpi=int(dpi), frameon=False)
    ax = pyplot.Axes(fig, [0, 0, 1, 1])
    ax.set_axis_off()
    fig.add_axes(ax)
    # plot display
    ax.axis([0, dispsize[0], 0, dispsize[1]])
    ax.imshow(screen)  # , origin='upper')
    del screen
    return fig, ax


def cluster_points(points, duration=20):

    TIME_VAL = 100000

    nb = min(50, len(points['x'])/10)
    if nb == 0:
        return points
    #affinity_prop = cluster.AffinityPropagation(affinity="euclidean", max_iter=50)
    affinity_prop = cluster.KMeans(n_clusters=int(nb), precompute_distances=True)
    #affinity_prop = cluster.MeanShift()
    #print len(points['x'])
    X = np.zeros([len(points['x']), 3])
    #print X
    for i in range(len(points['x'])):
        X[i][0] = points['x'][i]
        X[i][1] = points['y'][i]
        X[i][2] = points['timestamp'][i]/TIME_VAL

    affinity_prop.fit(X)

    centers = affinity_prop.cluster_centers_
    labels = affinity_prop.labels_
    #print labels

    cluster_size = np.zeros(len(centers))
    for i in range(len(labels)):
        cluster_size[labels[i]] += 1

    cluster_size = cluster_size[np.argsort(centers[:, 2])]

    centers = centers[np.argsort(centers[:, 2])]

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

