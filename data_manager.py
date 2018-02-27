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
import gc
import os
import sys
from contextlib import closing
from multiprocessing import Pool

import config
import image_data
import numpy as np
import user_data
from PIL import Image


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
    def __init__(self, project_name, image_list=None, user_dir="/users.csv", user_id=None, ml_out_dir=None):
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
        self.nb_images = 0
        self.nb_users = 0
        self.ml_out_dir = ml_out_dir

        # load ImageData objects from files
        print "Loading image data to memory..."
        for image in images:
            id = image.split('_')[1]
            if image.startswith("image") and (image_list is None or id in image_list):
                self.image_list.append(image_data.Image_data(project_name, image, self))
                self.nb_images += 1
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
            for j in range(len(data[i])):
                if data[0][j] == 'M':
                    m_vars[data[1][j]] = data[i][j]
                elif data[0][j] == 'Y':
                    y_vars[data[1][j]] = data[i][j]
            if user_id is None or m_vars['ID CYTOMINE'] == user_id:
                u = user_data.User_data(self.image_list, m_vars['ID CYTOMINE'], self, y_vars, m_vars)
                self.user_list.append(u)
                self.nb_users += 1

        f.close()
        for image in self.image_list:
            image.init_user_data_link(self.user_list)

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
        return out


    def var1_nb_im_visited(self, out):
        """
        For each user, appends their associated number of images visited to the output 2D list
        :param out: output 2D array
        :return: out array
        """
        out[0].append('X')
        out[1].append('NB IMAGES VISITED')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].nb_ims_visited())
        return out

    def var2_total_nb_positions(self, out):
        """
        For each user, appends their associated total number of positions to the output 2D list
        :param out: output 2D array
        :return: out array
        """
        out[0].append('X')
        out[1].append('TOTAL NB POSITIONS')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].total_nb_positions())
        return out

    def var3_average_nb_positions(self, out):
        """
        For each user, appends their associated average number of positions over all the images visited to the output 2D list
        :param out: output 2D array
        :return: out array
        """
        out[0].append('X')
        out[1].append('AVG NB POSITIONS')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].avg_nb_positions_visited())
        return out

    def var4_median_nb_positions(self, out):
        """
        For each user, appends their associated median number of positions over all the images visited to the output 2D list
        :param out: output 2D array
        :return: out array
        """
        out[0].append('X')
        out[1].append('MEDIAN NB POSITIONS')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].median_nb_positions())
        return out

    def var5_total_time(self, out):
        """
        For each user, appends their associated total time over all the images visited to the output 2D list
        :param out: output 2D array
        :return: out array
        """
        out[0].append('X')
        out[1].append('TOTAL IMAGE VIEWING TIME (s)')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].total_time_spent())
        return out

    def var6_avg_time(self, out):
        """
        For each user, appends their associated average time over all the images visited to the output 2D list
        :param out: output 2D array
        :return: out array
        """
        out[0].append('X')
        out[1].append('AVG IMAGE VIEWING TIME (s)')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].avg_time_spent())
        return out

    def var7_median_time(self, out):
        """
        For each user, appends their associated median time over all the images visited to the output 2D list
        :param out: output 2D array
        :return: out array
        """
        out[0].append('X')
        out[1].append('MEDIAN IMAGE VIEWING TIME (s)')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].median_time_spent())
        return out

    def var8_position_zooms(self, out):
        """
        For each user, appends their associated total number of positions for each zoom to the output 2D list (EG 10 variables)
        :param out: output 2D array
        :return: out array
        """
        for i in range(config.MAX_ZOOM):
            out[0].append('X')
            out[1].append('NB POSITIONS AT ZOOM ' + str(i + 1))

        for i in range(len(self.user_list)):
            array = self.user_list[i].zoom_position_number()
            for j in range(len(array)):
                out[i + 2].append(array[j])
        return out

    def var9_avg_position_zooms(self, out):
        """
        For each user, appends their associated average zoom over all images visited to the output 2D list
        :param out: output 2D array
        :return: out array
        """
        out[0].append('X')
        out[1].append('AVERAGE ZOOM')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].zoom_position_avg())
        return out

    def var10_median_position_zooms(self, out):
        """
        For each user, appends their associated median zoom over all images visited to the output 2D list
        :param out: output 2D array
        :return: out array
        """
        out[0].append('X')
        out[1].append('MEDIAN ZOOM')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].zoom_position_median())
        return out

    def var11_total_annotation_actions(self, out):
        """
        For each user, appends their associated total AnnotationActions to the output 2D list (EG 10 variables)
        :param out: output 2D array
        :return: out array
        """
        out[0].append('X')
        out[1].append('TOTAL NB ANNOTATION ACTIONS')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].total_annotation_actions())
        return out

    def var12_avg_annotation_actions(self, out):
        """
        For each user, appends their associated average AnnotationActions over all images visited to the output 2D list (EG 10 variables)
        :param out: output 2D array
        :return: out array
        """
        out[0].append('X')
        out[1].append('AVG NB ANNOTATION ACTIONS')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].avg_annotation_actions())
        return out

    def var13_median_annotation_actions(self, out):
        """
        For each user, appends their associated median AnnotationActions over all images visited to the output 2D list (EG 10 variables)
        :param out: output 2D array
        :return: out array
        """
        out[0].append('X')
        out[1].append('MEDIAN NB ANNOTATION ACTIONS')
        for i in range(len(self.user_list)):
            out[i + 2].append(self.user_list[i].median_annotation_actions())
        return out

    def var14_avg_position_by_zoom(self, out):
        """
        For each user, appends their associated average number of positions for each zoom to the output 2D list (EG 10 variables)
        :param out: output 2D array
        :return: out array
        """
        for i in range(config.MAX_ZOOM):
            out[0].append('X')
            out[1].append('AVG NB POSITIONS AT ZOOM ' + str(i + 1))

        for i in range(len(self.user_list)):
            array = self.user_list[i].zoom_position_number_avg()
            for j in range(len(array)):
                out[i + 2].append(array[j])
        return out

    def var15_median_position_by_zoom(self, out):
        """
        For each user, appends their associated median number of positions for each zoom to the output 2D list (EG 10 variables)
        :param out: output 2D array
        :return: out array
        """
        for i in range(config.MAX_ZOOM):
            out[0].append('X')
            out[1].append('MEDIAN NB POSITIONS AT ZOOM ' + str(i + 1))

        for i in range(len(self.user_list)):
            array = self.user_list[i].zoom_position_number_median()
            for j in range(len(array)):
                out[i + 2].append(array[j])
        return out

    def var16_user_image_score_per_image(self, out):
        """
        For each image, give a score on how well the user has observed the images and their respective annotations (1 var per image)
        Also outputs the average score over all the images as another variable
        :param out: output 2D array
        :return: out array
        """
        u_list = []
        for i in range(len(self.user_list)):
            u_list.append(self.user_list[i].user_id)

        im_len = 0
        for im in self.image_list:
            if len(im.user_positions) > 0:
                im_len += 1
                out[0].append('X')
                out[1].append("USER SCORE AT IMAGE " + str(im.image_id))
                scores = im.score_users(u_list)
                for i in range(len(self.user_list)):
                    out[i+2].append(scores[i])

        s_index = len(out[0]) - im_len
        s_len = len(out[0])
        out[0].append('X')
        out[1].append("AVERAGE USER SCORE")
        for i in range(len(self.user_list)):
            avg = 0
            for j in range(s_index, s_len):
                avg += max(float(out[i+2][j]), 0)
            avg = avg/im_len
            out[i+2].append(avg)

        return out


    def var17_per_image_info(self, out):
        """
        Adds Number of positions, time spent, ann actions, and zoom nb at image <x> to output
        :param out: output 2D list
        :return: out
        """
        for im in self.image_list:
            if len(im.user_positions) > 0:
                out[0].append('X')
                out[1].append("NB POSITIONS AT IMAGE " + str(im.image_id))
                for i in range(len(self.user_list)):
                    nb = self.user_list[i].number_of_positions(im.image_id)
                    out[i + 2].append(nb)
                out[0].append('X')
                out[1].append("TIME SPENT AT IMAGE " + str(im.image_id))
                for i in range(len(self.user_list)):
                    nb = self.user_list[i].time_spent(im.image_id)
                    out[i + 2].append(nb)
                out[0].append('X')
                out[1].append("NB OF ANNOTATION ACTIONS AT IMAGE " + str(im.image_id))
                for i in range(len(self.user_list)):
                    nb = self.user_list[i].number_of_annotation_actions(im.image_id)
                    out[i + 2].append(nb)
                max_z = im.max_zoom()
                for j in range(1, max_z + 1):
                    out[0].append('X')
                    out[1].append("NB OF POSITIONS WITH ZOOM " + str(j) + " AT IMAGE " + str(im.image_id))
                    for i in range(len(self.user_list)):
                        nb = self.user_list[i].number_of_positions_at_zoom(im.image_id, j)
                        out[i + 2].append(nb)

        return out


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

        # output file
        if self.ml_out_dir is None:
            csv_out_filename = 'learning_data.csv'
            stats_file = os.path.join(config.WORKING_DIRECTORY + self.project_name + "/",
                                      csv_out_filename)
        else:
            stats_file = self.ml_out_dir

        f = open(stats_file, "wb")
        csv_out = csv.writer(f)

        # calculate and add all variables in the 2D list
        self.add_user_metadata(out)
        self.var1_nb_im_visited(out)
        self.var2_total_nb_positions(out)
        self.var3_average_nb_positions(out)
        self.var4_median_nb_positions(out)
        self.var5_total_time(out)
        self.var6_avg_time(out)
        self.var7_median_time(out)
        self.var8_position_zooms(out)
        self.var9_avg_position_zooms(out)
        self.var10_median_position_zooms(out)
        self.var11_total_annotation_actions(out)
        self.var12_avg_annotation_actions(out)
        self.var13_median_annotation_actions(out)
        self.var14_avg_position_by_zoom(out)
        self.var15_median_position_by_zoom(out)
        self.var16_user_image_score_per_image(out)
        self.var17_per_image_info(out)

        self.var_results(out)

        # write data into file
        csv_out.writerow(out[0])
        for i in range(len(self.user_list)):
            csv_out.writerow(out[i + 1])

        f.close()

    def write_gazemaps(self):
        """
        Writes all different image visualisation for all user/images
        Note, Gazemaps take up a lot of memory, therefore it needs to be freed after being used
        :return: Nothing
        """

        for image in self.image_list:
            #todo : only 1217722 atm
            if image.image_id == "1217722":
                image.generate_all_heatmaps()
                image.save_all_heatmaps()
                image.save_all_heatmaps_ln()
                image.save_all_heatmaps_by_image()
                image.save_all_raw()
                image.save_all_scanpath()
                image.remove_all_heatmaps()
                gc.collect()

        for user in self.user_list:
            #todo : only 3425935 atm
            if user.user_id == "3425935":
                for im_id in user.image_data:
                    image = user.image_data[im_id]
                    image.generate_heatmap(user.user_id)
                user.save_all_heatmaps_by_user()
                for im_id in user.image_data:
                    image = user.image_data[im_id]
                    image.remove_heatmap(user.user_id)
                gc.collect()


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
    ml_info = None
    ml_out_dir = None
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
            ml_info = str(args[i+1])
            i += 2
        elif args[i] == "-M":
            ml = True
            i += 1
        elif args[i] == "-o" and (i+1) < len(args):
            ml_out_dir = str(args[i+1])
            i += 2
        else:
            error_msg()
            return

    image_list = None
    if files is True:
        f_image_list = open(files_info, "rb")
        csv_in = csv.reader(f_image_list)
        data_users = list(csv_in)
        image_list = []
        for u_tmp in data_users:
            image_list.append(str(u_tmp[0]))
        f_image_list.close()
    elif files is False:
        image_list = [files_info]

    manager = Data_manager(project_name, ml_out_dir=ml_out_dir, image_list=image_list)

    manager.write_ml_csv()
    ## todo rest of init


if __name__ == '__main__':

    ## todo : init with more args
    if len(sys.argv) != 2:
        handle_args(sys.argv)
    else:
        manager = Data_manager(sys.argv[1])
        print manager
        print "Generating ML data..."
        manager.write_ml_csv()
        #print "Generating Gazemaps..."
        #manager.write_gazemaps()

