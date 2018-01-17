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

import os
import sys
import csv
import config
import user_data
from dictionary_data import parse_positions, parse_annotations, parse_annotation_actions
from  gazemap import make_heatmap, save_heatmap, draw_raw, draw_scanpath, cluster_points
from PIL import Image
import numpy as np
import gc


class Image_data:



    def __init__(self, project_name, image_dir, manager):
        """
        Creates an Image data object containing image info and position info
        for all the users that have positions in a dictionary. It loads
        :param project_name: gold/silver
        :param image_dir: image_xxxxx
        """
        self.manager = manager
        self.image_id = image_dir.split('_')[1]
        self.image_dir = config.WORKING_DIRECTORY + project_name + "/images/" + image_dir + "/"
        self.positions_dir = self.image_dir + "user_positions/"
        self.annotations_dir = self.image_dir + "user_annotations/"
        self.ref_annotation_dir = self.image_dir + "reference_cytomine_annotations.csv"
        self.annotation_actions_dir = self.image_dir + "user_actions/"
        self.user_positions = {}
        self.user_actions = {}
        self.ref_annotations = None
        self.gaussians = {'zoom_4': None,
                          'zoom_5': None,
                          'zoom_6': None,
                          'zoom_7': None,
                          'zoom_8': None,
                          'zoom_9': None,
                          'zoom_10': None}
        self.image = Image.open(self.image_dir + "image.png")
        self.rescaled_width, self.rescaled_height = self.image.size
        self.user_data = {}

        u_positions_files = os.listdir(self.positions_dir)
        for pos in u_positions_files:
            f = open(self.positions_dir + pos, 'rb')
            pos_id = pos.split('_')[0]
            csv_in = csv.reader(f)
            data = list(csv_in)
            data.pop(0)
            f.close()
            pos_data = parse_positions(data, self, calc_gauss=True)
            self.user_positions[pos_id] = pos_data

        try:
            f = open(self.ref_annotation_dir, 'rb')
        except:
            f = None
        if f is not None:
            csv_in = csv.reader(f)
            data = list(csv_in)
            data.pop(0)
            f.close()
            ann_data = parse_annotations(data)
            self.ref_annotations = ann_data

        u_action_files = os.listdir(self.annotation_actions_dir)
        for pos in u_action_files:
            f = open(self.annotation_actions_dir + pos, 'rb')
            pos_id = pos.split('_')[0]
            csv_in = csv.reader(f)
            data = list(csv_in)
            data.pop(0)
            f.close()
            action_data = parse_annotation_actions(data, self.user_positions[pos_id], self.ref_annotations)
            self.user_actions[pos_id] = action_data


    def init_user_data_link(self, user_data):
        for user in user_data:
            if user.user_id in self.user_positions:
                self.user_data[user.user_id] = user
                user.image_data[self.image_id] = self

    def generate_heatmap(self, user_id):
        pos = self.user_positions[user_id]
        pos['heatmap'] = make_heatmap(pos, (self.rescaled_width, self.rescaled_height), self)

    def generate_all_heatmaps(self):
        for u_id in self.user_positions:
            self.generate_heatmap(u_id)

    def remove_heatmap(self, user_id):
        pos = self.user_positions[user_id]
        heatmap = pos['heatmap']
        pos['heatmap'] = None
        del heatmap

    def remove_all_heatmaps(self):
        for u_id in self.user_positions:
            self.remove_heatmap(u_id)
        gc.collect()

    def save_all_heatmaps_by_image(self):
        rgb_im = self.image.convert('RGB')
        rgb_im.save('converted_image.jpg')
        dir = self.image_dir + "gazemaps_image_method/"
        if not os.path.exists(dir):
            os.makedirs(dir)
        max_val = 0
        avg_val = 0
        l = 0
        for u_id in self.user_positions:
            pos = self.user_positions[u_id]
            heatmap = np.copy(pos['heatmap'])
            heatmap = heatmap + 1
            heatmap = np.log(heatmap)
            tmp = np.max(heatmap)
            max_val = max(tmp, max_val)
            if len(heatmap[heatmap > 0]) > 0:
                avg_val = np.mean(heatmap[heatmap > 0])
                l = l + 1
            del heatmap
        if l == 0:
            os.remove('converted_image.jpg')
            return

        avg_val = avg_val/l

        for u_id in self.user_positions:
            out = dir + u_id + "_heatmap.png"
            pos = self.user_positions[u_id]
            heatmap = np.copy(pos['heatmap'])
            heatmap = heatmap + 1
            heatmap = np.log(heatmap)
            heatmap[0][0] = max_val
            save_heatmap(heatmap, (self.rescaled_width, self.rescaled_height), imagefile='converted_image.jpg', savefilename=out, alpha=0.5, avg=avg_val)
            del heatmap
        gc.collect()
        os.remove('converted_image.jpg')

    def save_all_heatmaps_ln(self):
        rgb_im = self.image.convert('RGB')
        rgb_im.save('converted_image.jpg')
        dir = self.image_dir + "gazemaps_ln_method/"
        if not os.path.exists(dir):
            os.makedirs(dir)
        for u_id in self.user_positions:
            out = dir + u_id + "_heatmap.png"
            pos = self.user_positions[u_id]
            heatmap = np.copy(pos['heatmap'])
            heatmap = heatmap + 1
            heatmap = np.log(heatmap)
            save_heatmap(heatmap, (self.rescaled_width, self.rescaled_height), imagefile='converted_image.jpg', savefilename=out, alpha=0.5)
            del heatmap
        gc.collect()
        os.remove('converted_image.jpg')

    def save_all_heatmaps(self):
        rgb_im = self.image.convert('RGB')
        rgb_im.save('converted_image.jpg')
        dir = self.image_dir + "gazemaps_basic/"
        if not os.path.exists(dir):
            os.makedirs(dir)
        for u_id in self.user_positions:
            out = dir + u_id + "_heatmap.png"
            pos = self.user_positions[u_id]
            heatmap = np.copy(pos['heatmap'])
            save_heatmap(heatmap, (self.rescaled_width, self.rescaled_height), imagefile='converted_image.jpg', savefilename=out, alpha=0.5)
            del heatmap
        gc.collect()
        os.remove('converted_image.jpg')

    def save_all_raw(self):
        rgb_im = self.image.convert('RGB')
        rgb_im.save('converted_image.jpg')
        del rgb_im
        dir = self.image_dir + "raw_points_images/"
        if not os.path.exists(dir):
            os.makedirs(dir)
        for u_id in self.user_positions:
            out = dir + u_id + "_points.png"
            pos = self.user_positions[u_id]
            draw_raw(pos, (self.rescaled_width, self.rescaled_height), imagefile='converted_image.jpg', savefilename=out)
        #gc.collect()
        os.remove('converted_image.jpg')

    def save_all_scanpath(self):
        rgb_im = self.image.convert('RGB')
        rgb_im.save('converted_image.jpg')
        dir = self.image_dir + "scanpath_images/"
        if not os.path.exists(dir):
            os.makedirs(dir)
        for u_id in self.user_positions:
            out = dir + u_id + "_scanpath.png"
            pos = self.user_positions[u_id]
            tmp = cluster_points(pos)
            draw_scanpath(tmp, (self.rescaled_width, self.rescaled_height), imagefile='converted_image.jpg', savefilename=out)
        gc.collect()
        os.remove('converted_image.jpg')


    def __repr__(self):
        return "image :" + str(self.image_id) + ", pos :" + str(len(self.user_positions)) + ", links :" + str(len(self.user_data)) + "\n"

    def __str__(self):
        return "image :" + str(self.image_id) + ", pos :" + str(len(self.user_positions)) + ", links :" + str(len(self.user_data)) + "\n"



