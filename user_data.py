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
import config
import sys
import numpy as np
import image_data
from gazemap import save_heatmap
import gc

class User_data:

    def __init__(self, image_data_list, user_id, manager, practical, theory):
        self.positions = {}
        self.time_on_img = {}
        self.user_id = user_id
        self.manager = manager
        self.image_data = {}
        self.grade_theory = theory
        self.grade_practical = practical

        for image in image_data_list:
            if image.user_positions.get(str(user_id)) is not None:
                pos = image.user_positions[str(user_id)]
                im_id = image.image_id
                self.positions[str(im_id)] = pos

    def nb_ims_visited(self):
        return len(self.positions)

    def total_nb_positions(self):
        ret = 0
        for im in self.positions.values():
            ret += len(im['x'])
        return ret

    def median_nb_positions(self):
        if self.nb_ims_visited() == 0:
            return 0

        positions = np.zeros(self.nb_ims_visited())
        i = 0
        for im in self.positions.values():
            positions[i] = len(im['x'])
            i += 1
        positions = np.sort(positions)

        return positions[np.int(self.nb_ims_visited()/2)]

    def avg_nb_positions_visited(self):
        if self.nb_ims_visited() == 0:
            return 0
        return float(self.total_nb_positions()) / float(self.nb_ims_visited())

    def avg_nb_positions(self):
        return float(self.total_nb_positions()) / float(self.manager.nb_images())

    def time_spent(self, im_id):
        positions = self.positions[im_id]
        timestamps = positions['timestamp']
        i = 1
        time_on_image = 0.0
        while i < len(timestamps):
            ## timestamps are spaced at a interval of a maximum 5000ms
            if timestamps[i] - timestamps[i - 1] < 6000:
                time_on_image += timestamps[i] - timestamps[i - 1]
                i += 1
            else:
                i += 2
        self.time_on_img[im_id] = time_on_image/1000.0
        return time_on_image/1000.0

    def total_time_spent(self):
        ret = 0.0
        for im_id in self.positions:
            if im_id in self.time_on_img:
                ret += self.time_on_img[im_id]
            else:
                ret += self.time_spent(im_id)
        return ret

    def avg_time_spent(self):
        if self.nb_ims_visited() == 0:
            return 0
        return float(self.total_time_spent()) / float(self.nb_ims_visited())

    def median_time_spent(self):
        if self.nb_ims_visited() == 0:
            return 0

        time_array = np.zeros(self.nb_ims_visited())
        i = 0
        for im_id in self.positions:
            if im_id in self.time_on_img:
                time_array[i] = self.time_on_img[im_id]
            else:
                time_array[i] = self.time_spent(im_id)
            i += 1
        time_array = np.sort(time_array)

        return time_array[np.int(self.nb_ims_visited()/2)]

    def zoom_position_number(self):
        ret = np.zeros(config.MAX_ZOOM)
        for im_id in self.positions:
            p = self.positions[im_id]
            zooms = p['zoom']
            for i in range(len(zooms)):
                ret[zooms[i] - 1] += 1
        return ret

    def zoom_position_avg(self):
        ret = 0
        total = 0
        for im_id in self.positions:
            p = self.positions[im_id]
            zooms = p['zoom']
            for i in range(len(zooms)):
                ret += zooms[i]
                total += 1
        if total == 0:
            return 0
        return float(ret)/float(total)

    def zoom_position_median(self):
        ret = []
        total = 0
        for im_id in self.positions:
            p = self.positions[im_id]
            zooms = p['zoom']
            for i in range(len(zooms)):
                ret.append(zooms[i])
                total += 1

        ret.sort()
        if total == 0:
            return 0
        return ret[int(total/2)]

    def save_all_heatmaps_by_user(self):

        dir = config.WORKING_DIRECTORY  + self.manager.project_name + "/users/"
        if not os.path.exists(dir):
            os.makedirs(dir)
        dir = dir + "user_" + self.user_id + "/"
        if not os.path.exists(dir):
            os.makedirs(dir)
        dir = dir + "gazemaps_image_method/"
        if not os.path.exists(dir):
            os.makedirs(dir)

        max_val = 0
        avg_val = 0
        l = 0
        for im_id in self.image_data:
            pos = self.image_data[im_id].user_positions[self.user_id]
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
            gc.collect()
            return

        avg_val = avg_val/l

        for im_id in self.image_data:
            rgb_im = self.image_data[im_id].image.convert('RGB')
            rgb_im.save('converted_image.jpg')

            out = dir + im_id + "_heatmap.png"
            pos = self.image_data[im_id].user_positions[self.user_id]
            heatmap = np.copy(pos['heatmap'])
            heatmap = heatmap + 1
            heatmap = np.log(heatmap)
            heatmap[0][0] = max_val
            save_heatmap(heatmap, (self.image_data[im_id].rescaled_width, self.image_data[im_id].rescaled_height), imagefile='converted_image.jpg', savefilename=out, alpha=0.5, avg=avg_val)
            del heatmap
            os.remove('converted_image.jpg')
        gc.collect()

    def total_annotation_actions(self):
        ret = 0
        for im_id in self.image_data:
            im = self.image_data[im_id]
            if self.user_id in im.user_actions:
                actions = im.user_actions[self.user_id]
                ret += len(actions['id'])

        return ret

    def avg_annotation_actions(self):
        if self.nb_ims_visited() == 0:
            return 0
        return float(self.total_annotation_actions())/float(self.nb_ims_visited())

    def median_annotation_actions(self):
        if self.nb_ims_visited() == 0:
            return 0
        ret = np.zeros(self.nb_ims_visited())
        i = 0
        for im_id in self.image_data:
            im = self.image_data[im_id]
            if self.user_id in im.user_actions:
                actions = im.user_actions[self.user_id]
                ret[i] = len(actions['id'])
            i += 1
        ret = np.sort(ret)
        return ret[np.int(len(ret)/2)]

    def get_grade_practical(self):
        return self.grade_practical

    def get_grade_theory(self):
        return self.grade_theory

    def __repr__(self):
        return "user :" + str(self.user_id) + ", positions :" + str(len(self.positions)) + ", links :" + str(len(self.image_data)) + "\n"

    def __str__(self):
        return "user :" + str(self.user_id) + ", positions :" + str(len(self.positions)) + ", links :" + str(len(self.image_data)) + "\n"
