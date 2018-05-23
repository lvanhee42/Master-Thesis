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
from gazemap import study_heatmap

__author__          = "Vanhee Laurent <laurent.vanhee@student.uliege.ac.be>"
__copyright__       = "Copyright 2010-2017 University of Liège, Belgium, http://www.cytomine.be/"


from PIL import Image

import image_data
import user_data
import module_data
import config
import os
import sys
import csv
import numpy as np
from multiprocessing import Pool
import gc
from contextlib import  closing
from progress.bar import ChargingBar, Bar
import time
import datetime
import calendar
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle


def initialise_image(data):
    """
    Inits a Image data object
    :param data: triple input variable, (project_name, image_name, data_manger instance)
    :return: ImageData object
    """
    project_name, image_name, manager = data
    return image_data.Image_data(project_name, image_name, manager)

def parallelize_image_init(map_array):
    """
    Method to parallelize image_data initiation
    NOTE : ATM after initializing all the objects, doing methods with heavy memory
    manipulation causes memory leaks.
    :param map_array: array of triple input variable, (project_name, image_name, data_manger instance)
    :return: A list of ImageData objects
    """
    with closing(Pool(16, maxtasksperchild=1000)) as p:
        ret = p.map(initialise_image, map_array)
    p.join()
    return ret

class Data_manager:
    """
    Data Manager class, manages user and image data.
    """
    def __init__(self, project_name, image_list=None, user_dir="/users.csv", user_list=None, ml_out_dir=None):
        """
        Inits the object
        :param project_name: project name (EG "gold")
        :param image_list: Optional, list of image Ids to load to memory (If None, uses all images)
        :param user_dir: Optional (preset), Directory of user metadata. This file contains data for
                each user including name, grades, and etc...
        :param user_id: Optional, preset a user ID to only do operations on that user
        """

        # init vars
        self.project_name = project_name
        images = os.listdir(config.WORKING_DIRECTORY + project_name + "/images/")
        self.image_list = []
        self.user_list = []
        self.module_list = []
        self.nb_images = 0
        self.nb_users = 0
        self.ml_out_dir = ml_out_dir

        # load ImageData objects from files
        if image_list is None:
            bar = ChargingBar('Loading Image Data', max=len(images), stream=sys.stdout)
        else:
            bar = ChargingBar('Loading Image Data', max=len(image_list), stream=sys.stdout)
        bar.start()
        for image in images:
            id = image.split('_')[1]
            if image.startswith("image") and (image_list is None or id in image_list):
                self.image_list.append(image_data.Image_data(project_name, image, self, user_list))
                self.nb_images += 1
                bar.next()
        bar.finish()
        #map_array = []
        #for image in images:
        #    if image.startswith("image"):
        #        map_array.append((project_name, image, self))
        #        self.nb_images += 1
        #self.image_list = parallelize_image_init(map_array)

        # load UserData objects from files
        print "Loading user data to memory..."
        f = open(config.WORKING_DIRECTORY + project_name + user_dir, 'rb')
        csv_in = csv.reader(f)
        data = list(csv_in)
        for i in range(2, len(data)):
            y_vars = {}
            m_vars = {}
            x_vars = {}
            for j in range(len(data[i])):
                if data[0][j] == 'M':
                    m_vars[data[1][j]] = data[i][j]
                elif data[0][j] == 'Y':
                    y_vars[data[1][j]] = data[i][j]
                elif data[0][j] == 'X':
                    x_vars[data[1][j]] = data[i][j]
            if user_list is None or m_vars['CYTOMINE ID'] in user_list:
                u = user_data.User_data(self.image_list, m_vars['CYTOMINE ID'], self, y_vars, m_vars, x_vars)
                self.user_list.append(u)
                self.nb_users += 1

        f.close()
        for image in self.image_list:
            image.init_user_data_link(self.user_list)

        f = open(config.WORKING_DIRECTORY + project_name + "/timeline.csv", 'rb')
        csv_in = csv.reader(f)
        data = list(csv_in)
        for i in range(1, len(data)):
            row = data[i]
            m = module_data.Module_data(row, self.image_list, self, self.user_list)
            self.module_list.append(m)
        f.close()


    def __repr__(self):
        return "NbIm : " + str(self.nb_images) + ", NbUsers : " + str(self.nb_users) + "\n"

    def __str__(self):
        return "NbIm : " + str(self.nb_images) + ", NbUsers : " + str( self.nb_users) + "\n"

    def nb_users(self):
        """
        :return: Number of users (int)
        """
        return self.nb_users

    def nb_images(self):
        """
        :return: Number of images (int)
        """
        return self.nb_images

    def add_user_metadata(self, out):
        """
        Appends every user ID, first name, last name, and email to the output 2D list
        :param out: output 2D array
        :return: out array
        """
        for i in range(len(self.user_list)):
            m_vars = self.user_list[i].m_vars
            if i == 0:
                out.append([])
                out.append([])
                for k in m_vars:
                    out[0].append('M')
                    out[1].append(k)
            for k in m_vars:
                out.append([])
                out[i + 2].append(m_vars[k])

        for i in range(len(self.user_list)):
            m_vars = self.user_list[i].x_vars
            if i == 0:
                out.append([])
                out.append([])
                for k in m_vars:
                    out[0].append('X')
                    out[1].append(k)
            for k in m_vars:
                out.append([])
                out[i + 2].append(m_vars[k])
        return out


    def var1_nb_im_visited(self, out, bar):
        """
        For each user, appends their associated number of images visited to the output 2D list
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        out[0].append('X')
        out[1].append('NB IMAGES VISITED')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].nb_ims_visited())
        bar.next()
        return out

    def var2_total_nb_positions(self, out, bar):
        """
        For each user, appends their associated total number of positions to the output 2D list
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        out[0].append('X')
        out[1].append('TOTAL NB POSITIONS')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].total_nb_positions())
        bar.next()
        return out

    def var3_average_nb_positions(self, out, bar):
        """
        For each user, appends their associated average number of positions over all the images visited to the output 2D list
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        out[0].append('X')
        out[1].append('AVG NB POSITIONS')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].avg_nb_positions_visited())
        bar.next()
        return out

    def var4_median_nb_positions(self, out, bar):
        """
        For each user, appends their associated median number of positions over all the images visited to the output 2D list
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        out[0].append('X')
        out[1].append('MEDIAN NB POSITIONS')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].median_nb_positions())
        bar.next()
        return out

    def var5_total_time(self, out, bar):
        """
        For each user, appends their associated total time over all the images visited to the output 2D list
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        out[0].append('X')
        out[1].append('TOTAL IMAGE VIEWING TIME (s)')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].total_time_spent())
        bar.next()
        return out

    def var6_avg_time(self, out, bar):
        """
        For each user, appends their associated average time over all the images visited to the output 2D list
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        out[0].append('X')
        out[1].append('AVG IMAGE VIEWING TIME (s)')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].avg_time_spent())
        bar.next()
        return out

    def var7_median_time(self, out, bar):
        """
        For each user, appends their associated median time over all the images visited to the output 2D list
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        out[0].append('X')
        out[1].append('MEDIAN IMAGE VIEWING TIME (s)')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].median_time_spent())
        bar.next()
        return out

    def var8_position_zooms(self, out, bar):
        """
        For each user, appends their associated total number of positions for each zoom to the output 2D list (EG 10 variables)
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        for i in range(config.MAX_ZOOM):
            out[0].append('X')
            out[1].append('NB POSITIONS AT ZOOM ' + str(i + 1))

        k = 0
        tot = len(self.user_list)
        for i in range(len(self.user_list)):
            array = self.user_list[i].zoom_position_number()
            for j in range(len(array)):
                out[i + 2].append(array[j])
                k += 1
                if k > tot:
                    bar.next()
                    tot += len(self.user_list)
        return out

    def var9_avg_position_zooms(self, out, bar):
        """
        For each user, appends their associated average zoom over all images visited to the output 2D list
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        out[0].append('X')
        out[1].append('AVERAGE ZOOM')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].zoom_position_avg())
        bar.next()
        return out

    def var10_median_position_zooms(self, out, bar):
        """
        For each user, appends their associated median zoom over all images visited to the output 2D list
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        out[0].append('X')
        out[1].append('MEDIAN ZOOM')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].zoom_position_median())
        bar.next()
        return out

    def var11_total_annotation_actions(self, out, bar):
        """
        For each user, appends their associated total AnnotationActions to the output 2D list (EG 10 variables)
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        out[0].append('X')
        out[1].append('TOTAL NB ANNOTATION ACTIONS')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].total_annotation_actions())
        bar.next()
        return out

    def var12_avg_annotation_actions(self, out, bar):
        """
        For each user, appends their associated average AnnotationActions over all images visited to the output 2D list (EG 10 variables)
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        out[0].append('X')
        out[1].append('AVG NB ANNOTATION ACTIONS')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].avg_annotation_actions())
        bar.next()
        return out

    def var13_median_annotation_actions(self, out, bar):
        """
        For each user, appends their associated median AnnotationActions over all images visited to the output 2D list (EG 10 variables)
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        out[0].append('X')
        out[1].append('MEDIAN NB ANNOTATION ACTIONS')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].median_annotation_actions())
        bar.next()
        return out

    def var14_avg_position_by_zoom(self, out, bar):
        """
        For each user, appends their associated average number of positions for each zoom to the output 2D list (EG 10 variables)
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        for i in range(config.MAX_ZOOM):
            out[0].append('X')
            out[1].append('AVG NB POSITIONS AT ZOOM ' + str(i + 1))

        k = 0
        tot = len(self.user_list)
        for i in range(len(self.user_list)):
            array = self.user_list[i].zoom_position_number_avg()
            for j in range(len(array)):
                out[i + 2].append(array[j])
                k += 1
                if k > tot:
                    bar.next()
                    tot += len(self.user_list)
        return out

    def var15_median_position_by_zoom(self, out, bar):
        """
        For each user, appends their associated median number of positions for each zoom to the output 2D list (EG 10 variables)
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        for i in range(config.MAX_ZOOM):
            out[0].append('X')
            out[1].append('MEDIAN NB POSITIONS AT ZOOM ' + str(i + 1))

        k = 0
        tot = len(self.user_list)
        for i in range(len(self.user_list)):
            array = self.user_list[i].zoom_position_number_median()
            for j in range(len(array)):
                out[i + 2].append(array[j])
                k += 1
                if k > tot:
                    bar.next()
                    tot += len(self.user_list)
        return out

    def var16_user_image_score_per_image(self, out, bar):
        """
        For each image, give a score on how well the user has observed the images and their respective annotations (1 var per image)
        Also outputs the average score over all the images as another variable
        :param out: output 2D array
        :param bar: chargingbar
        :return: out array
        """
        u_list = []
        for i in range(len(self.user_list)):
            u_list.append(self.user_list[i].user_id)

        k = 0
        tot = len(self.user_list)
        im_len = 0
        cnt = 0
        for im in self.image_list:
            if len(im.user_positions) > 0:
                im_len += 1
                out[0].append('X')
                out[1].append("USER SCORE AT IMAGE " + str(im.image_id))
                cnt += 1
                scores, ann_scores = im.score_users(u_list)
                for i in range(len(self.user_list)):
                    out[i+2].append(scores[i])
                    k += 1
                    if k > tot:
                        bar.next()
                        tot += len(self.user_list)
                for i in range(im.nb_ref_annotations()):
                    cnt += 1
                    out[0].append('X')
                    out[1].append("SCORE OF ANNOTATION " + str(int(im.ref_annotations['id'][i])) + " AT IMAGE " + str(im.image_id))
                    for j in range(len(self.user_list)):
                        out[j+2].append(ann_scores[j][i])
                        k += 1
                        if k > tot:
                            bar.next()
                            tot += len(self.user_list)

        s_index = len(out[0]) - cnt
        s_len = len(out[0])
        out[0].append('X')
        out[1].append("AVERAGE USER SCORE")
        for i in range(len(self.user_list)):
            avg = 0
            for j in range(s_index, s_len):
                if "USER SCORE" in out[1][j]:
                    avg += max(float(out[i+2][j]), 0)
            avg = avg/im_len
            out[i+2].append(avg)
        bar.next()

        return out


    def var17_per_image_info(self, out, bar):
        """
        Adds Number of positions, time spent, ann actions, and zoom nb at image <x> to output
        :param out: output 2D list
        :param bar: chargingbar
        :return: out
        """
        k = 0
        tot = len(self.user_list)
        for im in self.image_list:
            if len(im.user_positions) > 0:
                out[0].append('X')
                out[1].append("NB POSITIONS AT IMAGE " + str(im.image_id))
                for i in range(len(self.user_list)):
                    nb = self.user_list[i].number_of_positions(im.image_id)
                    out[i + 2].append(nb)
                    k += 1
                    if k > tot:
                        bar.next()
                        tot += len(self.user_list)
                out[0].append('X')
                out[1].append("TIME SPENT AT IMAGE " + str(im.image_id))
                for i in range(len(self.user_list)):
                    nb = self.user_list[i].time_spent(im.image_id)
                    out[i + 2].append(nb)
                    k += 1
                    if k > tot:
                        bar.next()
                        tot += len(self.user_list)
                out[0].append('X')
                out[1].append("NB OF ANNOTATION ACTIONS AT IMAGE " + str(im.image_id))
                for i in range(len(self.user_list)):
                    nb = self.user_list[i].number_of_annotation_actions(im.image_id)
                    out[i + 2].append(nb)
                    k += 1
                    if k > tot:
                        bar.next()
                        tot += len(self.user_list)
                max_z = im.zoom_max
                for j in range(1, max_z + 1):
                    out[0].append('X')
                    out[1].append("NB OF POSITIONS WITH ZOOM " + str(j) + " AT IMAGE " + str(im.image_id))
                    for i in range(len(self.user_list)):
                        nb = self.user_list[i].number_of_positions_at_zoom(im.image_id, j)
                        out[i + 2].append(nb)
                        k += 1
                        if k > tot:
                            bar.next()
                            tot += len(self.user_list)

        return out

    def var18_module_variables(self, out, bar):
        """
        Adds most previously mentioned variables but in regards to modules
        :param out: output 2D array
        :param bar: chargingbar
        :return: out
        """
        for module in self.module_list:

            pos, avg, med, tot = module.nb_positions_total_avg_median()
            out[0].append("X")
            out[1].append("TOTAL NB IMAGES VISITED DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(tot[i])
            bar.next()

            out[0].append("X")
            out[1].append("TOTAL NB POSITIONS DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(pos[i])
            bar.next()

            out[0].append("X")
            out[1].append("AVG NB POSITIONS DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(avg[i])
            bar.next()

            out[0].append("X")
            out[1].append("MEDIAN NB POSITIONS DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(med[i])
            bar.next()

            time, avg, med = module.time_spent_total_avg_median()
            out[0].append("X")
            out[1].append("TOTAL TIME SPENT DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(time[i])
            bar.next()

            out[0].append("X")
            out[1].append("AVG TIME SPENT DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(avg[i])

            out[0].append("X")
            out[1].append("MEDIAN TIME SPENT DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(med[i])
            bar.next()

            pos, id = module.per_image_nb_positions()
            for i in range(len(pos)):
                out[0].append("X")
                out[1].append("NUMBER OF POSITIONS DURING MODULE " + module.id + " FOR IMAGE " + id[i])
                poss = pos[i]
                for j in range(len(poss)):
                    out[j + 2].append(poss[j])
                bar.next()

            pos, id = module.per_image_time_spent()
            for i in range(len(pos)):
                out[0].append("X")
                out[1].append("TIME SPENT DURING MODULE " + module.id + " FOR IMAGE " + id[i])
                poss = pos[i]
                for j in range(len(poss)):
                    out[j + 2].append(poss[j])
                bar.next()

            pos, id = module.per_image_ann_actions()
            for i in range(len(pos)):
                out[0].append("X")
                out[1].append("NB OF ANNOTATION ACTIONS DURING MODULE " + module.id + " FOR IMAGE " + id[i])
                poss = pos[i]
                for j in range(len(poss)):
                    out[j + 2].append(poss[j])
                bar.next()

            pos, id = module.per_image_zooms()
            for i in range(len(pos)):
                tmp1, tmp2 = id[i]
                out[0].append("X")
                out[1].append("NB OF POSITIONS WITH ZOOM " + str(tmp2) + " DURING MODULE " + module.id + " AT IMAGE " + str(tmp1))
                poss = pos[i]
                for j in range(len(poss)):
                    out[j + 2].append(poss[j])
                bar.next()


            avg, med, tot_l, avg_l, med_l = module.zooms()

            out[0].append("X")
            out[1].append("AVERAGE ZOOM DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(avg[i])
            bar.next()

            out[0].append("X")
            out[1].append("AVERAGE ZOOM DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(med[i])
            bar.next()

            for i in range(len(tot_l)):
                out[0].append("X")
                out[1].append("NB POSITIONS AT ZOOM " + str(i + 1) + " DURING MODULE " + module.id)
                poss = tot_l[i]
                for j in range(len(poss)):
                    out[j + 2].append(poss[j])
                bar.next()

            for i in range(len(avg_l)):
                out[0].append("X")
                out[1].append("AVG NB POSITIONS AT ZOOM " + str(i + 1) + " DURING MODULE " + module.id)
                poss = avg_l[i]
                for j in range(len(poss)):
                    out[j + 2].append(poss[j])
                bar.next()

            for i in range(len(med_l)):
                out[0].append("X")
                out[1].append("MEDIAN NB POSITIONS AT ZOOM " + str(i + 1) + " DURING MODULE " + module.id)
                poss = avg_l[i]
                for j in range(len(poss)):
                    out[j + 2].append(poss[j])
                bar.next()

            tot, avg, med = module.annotation_actions()
            out[0].append("X")
            out[1].append("TOTAL NB ANNOTATION ACTIONS DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(tot[i])
            bar.next()

            out[0].append("X")
            out[1].append("AVG NB ANNOTATION ACTIONS DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(avg[i])
            bar.next()

            out[0].append("X")
            out[1].append("MEDIAN NB ANNOTATION ACTIONS DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(med[i])
            bar.next()

            avg, per_img, per_ann, im_id, ann_id = module.user_scores()

            out[0].append('X')
            out[1].append("AVERAGE USER SCORE DURING MODULE " + module.id)
            for i in range(len(self.user_list)):
                out[i + 2].append(avg[i])
            bar.next()

            for i in range(len(per_img)):
                out[0].append('X')
                out[1].append("USER SCORE AT IMAGE " + str(im_id[i]) + " DURING MODULE " + module.id)
                poss = per_img[i]
                for j in range(len(poss)):
                    out[j + 2].append(poss[j])
                bar.next()

            for i in range(len(per_ann)):
                tmp1, tmp2 = ann_id[i]
                out[0].append("X")
                out[1].append("SCORE OF ANNOTATION " + str(tmp2) + " AT IMAGE " + str(tmp1) + " DURING MODULE " + module.id)
                poss = per_ann[i]
                for j in range(len(poss)):
                    out[j + 2].append(poss[j])
                bar.next()
        return out

    def var19_relative_time_worked(self, out, bar):
        """
        Adds the percent time worked on images during specific timeframes
        :param out: output 2D array
        :param bar: chargingbar
        :return: out
        """
        out[0].append('X')
        out[1].append('PERCENT TIME WORKED NIGHT')

        out[0].append('X')
        out[1].append('PERCENT TIME WORKED LATE')

        out[0].append('X')
        out[1].append('PERCENT TIME WORKED MORNING')


        for i in range(len(self.user_list)):
            n, l, m = self.user_list[i].relative_time_worked()
            out[i + 2].append(n)
            out[i + 2].append(l)
            out[i + 2].append(m)
        bar.next()
        bar.next()
        bar.next()
        return out

    def var20_nb_of_days_worked(self, out, bar):
        """
        Adds the number of days worked on cytomine for each user
        :param out: output 2D array
        :param bar: chargingbar
        :return: out
        """
        out[0].append('X')
        out[1].append('NUMBER OF DAYS WORKED')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].nb_of_different_days_worked())
        bar.next()

        return out

    def var21_module_percent_time(self, out, bar):
        """
        Adds the percent time worked on images of a module during respective timeframe
        :param out: output 2D array
        :param bar: chargingbar
        :return: out
        """
        for j in range(len(self.module_list)):
            out[0].append('X')
            out[1].append('PERCENT TIME WORKED DURING MODULE ' + str(j + 1))
            time = self.module_list[j].ratio_during_module()
            for i in range(len(self.user_list)):
                out[i + 2].append(time[i])
            bar.next()

        return out

    def var22_annotation_visit_order(self, out, bar):
        """
        Adds Annotation visit order for each user relative to all sucessive annotations
        :param out: output 2D array
        :param bar: chargingbar
        :return: out
        """
        for j in range(len(self.image_list)):
            ann = self.image_list[j].ref_annotations
            im_id = self.image_list[j].image_id
            if ann is not None:
                args = np.argsort(ann['localId'])
                for i in range(len(args) - 1):

                    ann1 = args[i]
                    ann2 = args[i + 1]
                    out[0].append('X')
                    out[1].append('ANNOTATION ' + str(int(ann['localId'][ann1])) + ' VISITED BEFORE ANNOTATION ' + str(int(ann['localId'][ann2])) + ' AT IMAGE ' + str(im_id))

                    var = self.image_list[j].annotation_order(ann1, ann2, self.user_list)
                    for k in range(len(self.user_list)):
                        out[k + 2].append(var[k])
                    bar.next()


    def var_results(self, out):
        """
        For each user, appends their associated practical and theoretical grades to the output 2D list (2 variables)
        :param out: output 2D array
        :return: out array
        """
        for i in range(len(self.user_list)):
            y_vars = self.user_list[i].y_vars
            if i == 0:
                for k in y_vars:
                    out[0].append('Y')
                    out[1].append(k)
            for k in y_vars:
                out[i + 2].append(y_vars[k])
        return out


    def write_ml_csv(self):
        """
        Writes the machine learning / info file containing user behavior
        :return: Nothing
        """

        # 2D list, 1st row contains variable title and each row after contains data for 1 user
        out = []

        bar = ChargingBar('Writing data file', max=2600, stream=sys.stdout)

        # calculate and add all variables in the 2D list
        self.add_user_metadata(out)
        self.var1_nb_im_visited(out, bar)
        self.var2_total_nb_positions(out, bar)
        self.var3_average_nb_positions(out, bar)
        self.var4_median_nb_positions(out, bar)
        self.var5_total_time(out, bar)
        self.var6_avg_time(out, bar)
        self.var7_median_time(out, bar)
        self.var8_position_zooms(out, bar)
        self.var9_avg_position_zooms(out, bar)
        self.var10_median_position_zooms(out, bar)
        self.var11_total_annotation_actions(out, bar)
        self.var12_avg_annotation_actions(out, bar)
        self.var13_median_annotation_actions(out, bar)
        self.var14_avg_position_by_zoom(out, bar)
        self.var15_median_position_by_zoom(out, bar)
        self.var16_user_image_score_per_image(out, bar)
        self.var17_per_image_info(out, bar)
        self.var18_module_variables(out, bar)
        self.var19_relative_time_worked(out, bar)
        self.var20_nb_of_days_worked(out, bar)
        self.var21_module_percent_time(out, bar)
        self.var22_annotation_visit_order(out, bar)

        self.var_results(out)

        # output file
        if self.ml_out_dir is None:
            csv_out_filename = 'learning_data.csv'
            stats_file = os.path.join(config.WORKING_DIRECTORY + self.project_name + "/",
                                      csv_out_filename)
        else:
            stats_file = self.ml_out_dir

        f = open(stats_file, "wb")
        csv_out = csv.writer(f)

        # write data into file
        print len(out[0])
        csv_out.writerow(out[0])
        for i in range(len(self.user_list)):
            csv_out.writerow(out[i + 1])

        f.close()
        bar.finish()

    def draw_timeline(self, params=None, key_dates=[], user_id = None):
        """
        Draws a timeline of all or a single user based on positions
        :param params: list of where the arrows will be displayed vertically for each module (0-1)
        :param key_dates: list Key dates to annotate to give more contex
        :param user_id: if mentioned only retrieves positions for this particular user.
        :return: None
        """
        start = datetime.datetime.strptime(config.start_time, "%Y-%m-%d %H:%M:%S")
        end = datetime.datetime.strptime(config.end_time, "%Y-%m-%d %H:%M:%S")
        if params is None:
            params = [0.99, 0.94, 0.99, 0.99, 0.99, 0.94]
        start_d = start.timetuple().tm_yday
        end_d = end.timetuple().tm_yday

        nb_days = end_d - start_d + 1
        array = [0 for i in range(nb_days)]
        for im in self.image_list:
            user_positions = im.user_positions
            if user_id is None:
                for pos in user_positions:
                    poss = user_positions[pos]
                    timestamps = poss['timestamp']
                    for i in range(len(timestamps)):
                        t = datetime.datetime.fromtimestamp(float(timestamps[i] / 1000.0))
                        day = t.timetuple().tm_yday
                        if day <= end_d:
                            array[day - start_d] += 1
            else:
                if user_id in user_positions:
                    poss = user_positions[user_id]
                    timestamps = poss['timestamp']
                    for i in range(len(timestamps)):
                        t = datetime.datetime.fromtimestamp(float(timestamps[i] / 1000.0))
                        day = t.timetuple().tm_yday
                        if day <= end_d:
                            array[day - start_d] += 1


        mods = []
        for j in range(len(self.module_list)):
            module = self.module_list[j]
            mod_array = [0 for i in range(nb_days)]
            for im_id in module.images:
                im = module.images[im_id]
                user_positions = im.user_positions
                if user_id is None:
                    for pos in user_positions:
                        poss = user_positions[pos]
                        timestamps = poss['timestamp']
                        for i in range(len(timestamps)):
                            t = datetime.datetime.fromtimestamp(float(timestamps[i] / 1000.0))
                            day = t.timetuple().tm_yday
                            if day <= end_d:
                                mod_array[day - start_d] += 1
                else:
                    if user_id in user_positions:
                        poss = user_positions[user_id]
                        timestamps = poss['timestamp']
                        for i in range(len(timestamps)):
                            t = datetime.datetime.fromtimestamp(float(timestamps[i] / 1000.0))
                            day = t.timetuple().tm_yday
                            if day <= end_d:
                                mod_array[day - start_d] += 1

            mods.append(mod_array)

        plt.figure(figsize=(25, 14), dpi=80, facecolor='w', edgecolor='k')
        plt.subplots_adjust(top=0.95)
        plt.subplots_adjust(bottom=0.05)
        plt.subplots_adjust(left=0.05)
        plt.subplots_adjust(right=0.90)
        colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
        indexes = [i for i in range(nb_days)]
        plt.plot(indexes, array)
        for i in range(len(mods)):
            mod_array = mods[i]
            plt.plot(indexes, mod_array, color=colors[i])

        for i in range(len(self.module_list)):
            param = params[i]
            module = self.module_list[i]
            start_mod = module.start_date
            end_mod = module.end_date
            start_m = start_mod.timetuple().tm_yday
            start_m = start_m - start_d
            end_m = end_mod.timetuple().tm_yday
            end_m = end_m - start_d
            plt.annotate(s='', xy=(start_m, param * max(array)), xytext=(end_m, param * max(array)), arrowprops=dict(arrowstyle='<->', color=colors[i]))
            plt.text(float(start_m + end_m) * 0.5, 1.005 * param * max(array), "Module " + str(i + 1), horizontalalignment='center', color=colors[i])
            plt.axvline(x=float(start_m), color='black')
            plt.axvline(x=float(end_m), color='black')

        days = []
        current = start
        prev_day_month = 0
        start_month_idx = 0
        end_month_idx = 0
        for i in range(nb_days):
            day_nb = current.timetuple().tm_mday
            day_month = current.timetuple().tm_mon
            day_month = calendar.month_name[day_month - 1]
            weekend = current.timetuple().tm_wday
            if weekend == 5 or weekend == 6:
                plt.axvspan(float(i) - 0.5, float(i) + 0.5, facecolor='#ffffcc', alpha=0.4)

            if prev_day_month > day_nb:
                end_month_idx = i - 1
                plt.text(float(start_month_idx + end_month_idx)*0.5, -0.04*max(array), day_month, horizontalalignment='center')
                plt.axvline(x=float(i) - 0.5, color='#babbbc')
                start_month_idx = end_month_idx

            days.append(day_nb)

            prev_day_month = day_nb
            current += datetime.timedelta(days=1)

        for i in range(len(key_dates)):
            val, name = key_dates[i]
            date = datetime.datetime.strptime(val + " 08:00", "%d/%m/%Y %H:%M")
            k_d = date.timetuple().tm_yday
            k_d = k_d - start_d
            plt.annotate(s='', xytext=(k_d, 0), xy=(k_d + 10, 0.2 * max(array)), arrowprops=dict(arrowstyle='<-', color='black'))
            plt.text(k_d + 10, 0.2 * max(array), name, horizontalalignment='left', color='black')

        handles = [Rectangle((0, 0), 1, 1, color=colors[c], ec="k") for c in range(len(self.module_list))]
        handles.append(Rectangle((0, 0), 1, 1, ec="k"))
        labels = ["Module " + str(i + 1) for i in range(len(self.module_list))]
        labels.append("Total")
        plt.legend(handles, labels, fontsize=14)
        x_tics = [j for j in range(nb_days)]
        #x_tics = x_tics[0:plot_size + 1]
        plt.xticks(x_tics, days, fontsize=4)
        if user_id is None:
            fname = config.WORKING_DIRECTORY + self.project_name + "/timeline" + datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + ".png"
        else:
            fname = config.WORKING_DIRECTORY + self.project_name + "/users/user_" + user_id + "/"
            if not os.path.exists(fname):
                os.makedirs(fname)
            fname = fname + "/timeline.png"
        plt.savefig(fname)
        plt.close('all')

    def draw_gazemaps(self):
        """
        Writes a reduced gazemap for all user/images
        Note, Gazemaps take up a lot of memory, therefore it needs to be freed after being used
        :return: Nothing
        """
        nb = 0
        for im in self.image_list:
            nb += im.nb_of_users()

        bar = Bar('Generating Heatmaps', max=nb, stream=sys.stdout)
        bar.start()

        for image in self.image_list:
            #if image.image_id == "1217722":
                #image.generate_all_heatmaps()
                #image.save_all_heatmaps()
                #image.save_all_heatmaps_ln()
                #image.save_all_heatmaps_by_image()
                image.save_all_heatmaps_reduced(bar)
                #image.remove_all_heatmaps()
                gc.collect()

        #for user in self.user_list:
            #if user.user_id == "3425935":
        #        for im_id in user.image_data:
        #            image = user.image_data[im_id]
        #            image.generate_heatmap(user.user_id)
        #        user.save_all_heatmaps_by_user()
        #        for im_id in user.image_data:
        #            image = user.image_data[im_id]
        #            image.remove_heatmap(user.user_id)
        #        gc.collect()
        bar.finish()

    def draw_all_timelines(self):
        """
        Draws all the timelines
        :return: None
        """
        self.draw_timeline(key_dates=[("24/04/2017", "White Exam"), ("12/06/2017", "Exam"), ("21/08/2017", "2nd Sess. Exam")])
        bar = Bar('Generating Timelines', max=len(self.user_list), stream=sys.stdout)
        bar.start()
        for u in self.user_list:
            u_id = u.user_id
            self.draw_timeline(key_dates=[("24/04/2017", "White Exam"), ("12/06/2017", "Exam"), ("21/08/2017", "2nd Sess. Exam")], user_id=u_id)
            bar.next()
        bar.finish()

    def draw_scanpaths(self):
        """
        Draws all the scanpaths for the user/image pairs
        :return: 
        """
        nb = 0
        for im in self.image_list:
            nb += im.nb_of_users()
        bar = Bar('Generating Scanpaths', max=nb, stream=sys.stdout)
        bar.start()

        for image in self.image_list:
            image.save_all_scanpath(bar)
        bar.finish()

    def draw_raw(self):
        """
        Draws all raw point visualisations for the user/image pairs.
        :return: 
        """
        nb = 0
        for im in self.image_list:
            nb += im.nb_of_users()
        bar = Bar('Generating raw points images', max=nb, stream=sys.stdout)
        bar.start()

        for image in self.image_list:
            image.save_all_raw(bar)
        bar.finish()


def error_msg():
    """
    Prints error message
    :return: Nothing
    """
    print "Format: image_data.py <project_name>\n"
    print "Options (-I and -U uses default settings if not specified):"
    print "  -U <user_id file_dir> :\n    CSV file with user IDs, Default at ../working/directory/<project_name>/users.csv\n    Applies library functions to the list of these users\n"
    print "  -u <user_id> :\n    Single user ID\n    Applies library functions to this user specifically\n"
    print "  -I <image_id_file_dir> :\n    CSV file with image IDs, Default takes all images in the ../working/directory/<project_name>/images directory\n    Applies library functions to the list of these images\n"
    print "  -i <image_id> :\n    Single image ID\n    Applies library functions to this image specifically\n"
    print "  -m <output_dir> :\n    Generates a CSV file containing evaluations on the users\n    <output_dir> is where that file is saved\n"
    print "  -M :\n    Generates a CSV file containing evaluations on the users\n    It is saved at ../working/directory/<project_name>/learning_data.csv\n"
    print "  -H :\n    Generates the Heatmaps for all the user/image pairs\n"
    print "  -S :\n    Generates the scanpaths for all the user/image pairs\n"
    print "  -T :\n    Generates the timelines for all the users\n"
    print "  -R :\n    Generates the raw point visualisations for all the user/image pairs\n"

def handle_args(args):
    """
    Handle args and executes code according (TODO : finish)
    :param args: list of input arguments
    :return: Nothing
    """
    i = 2
    users = None
    user_info = None
    files = None
    files_info = None
    ml = False
    scan = False
    raw = False
    timlines = False
    ml_out_dir = None
    heatmaps = False
    project_name = args[1]
    if not os.path.exists(config.WORKING_DIRECTORY + project_name):
        error_msg()
        return
    while i < len(args):
        if args[i] == "-U" and (i+1) < len(args):
            users = True
            user_info = str(args[i+1])
            i += 2
        elif args[i] == "-u" and (i+1) < len(args):
            users = False
            user_info = str(args[i+1])
            i += 2
        elif args[i] == "-I" and (i+1) < len(args):
            files = True
            files_info = str(args[i+1])
            i += 2
        elif args[i] == "-i" and (i+1) < len(args):
            files = False
            files_info = str(args[i+1])
            i += 2
        elif args[i] == "-m" and (i+1) < len(args):
            ml = True
            ml_out_dir = str(args[i+1])
            i += 2
        elif args[i] == "-M":
            ml = True
            i += 1
        elif args[i] == "-H":
            heatmaps = True
            i += 1
        elif args[i] == "-S":
            scan = True
            i += 1
        elif args[i] == "-T":
            timlines = True
            i += 1
        elif args[i] == "-R":
            raw = True
            i += 1
        else:
            error_msg()
            return

    image_list = None
    if files is True:
        f_image_list = open(files_info, "rb")
        csv_in = csv.reader(f_image_list)
        data_im = list(csv_in)
        image_list = []
        for i_tmp in data_im:
            image_list.append(str(i_tmp[0]))
        f_image_list.close()
    elif files is False:
        image_list = [files_info]

    user_list = None
    if users is True:
        f_user_list = open(user_info, 'rb')
        csv_in = csv.reader(f_user_list)
        data_user = list(csv_in)
        user_list = []
        for u_tmp in data_user:
            user_list.append(str(u_tmp[0]))
        f_user_list.close()
    elif users is False:
        user_list = [user_info]


    manager = Data_manager(project_name, ml_out_dir=ml_out_dir, image_list=image_list, user_list=user_list)
    print manager

    if ml:
        print "Generating ML data..."
        manager.write_ml_csv()
    if heatmaps:
        print "Generating Heatmaps..."
        manager.draw_gazemaps()
    if timlines:
        print "Generating Timelines..."
        manager.draw_all_timelines()
    if scan:
        print "Generating Scanpaths..."
        manager.draw_scanpaths()
    if raw:
        print "Generating Raw points images..."
        manager.draw_raw()
    #study_heatmap(manager.image_list[0])


if __name__ == '__main__':

    handle_args(sys.argv)
