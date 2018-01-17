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


from PIL import Image

import image_data
import user_data
import config
import os
import sys
import csv
import numpy as np
from multiprocessing import Pool
import gc
from contextlib import closing

def initialise_image(data):
    project_name, image_name, manager = data
    return image_data.Image_data(project_name, image_name, manager)

def parallelize_image_init(map_array):
    with closing(Pool(16, maxtasksperchild=1000)) as p:
        ret = p.map(initialise_image, map_array)
    p.join()
    return ret

class Data_manager:

    def __init__(self, project_name):
        self.project_name = project_name

        images = os.listdir(config.WORKING_DIRECTORY + project_name + "/images/")
        self.image_list = []
        self.user_list = []
        self.nb_images = 0
        self.nb_users = 0

        print "Loading image data to memory..."
        for image in images:
            if image.startswith("image"):
                self.image_list.append(image_data.Image_data(project_name, image, self))
                self.nb_images += 1
        #map_array = []
        #for image in images:
        #    if image.startswith("image"):
        #        map_array.append((project_name, image, self))
        #        self.nb_images += 1
        #self.image_list = parallelize_image_init(map_array)

        print "Loading user data to memory..."
        f = open(config.WORKING_DIRECTORY + project_name + "/users.csv", 'rb')
        csv_in = csv.reader(f)
        data = list(csv_in)
        data.pop(0)
        user_dir = []
        grades_p = []
        grades_t = []
        for row in data:
            user_dir.append(row[4])
            grades_t.append(float(row[5]))
            grades_p.append(float(row[6]))
        f.close()
        for i in range(len(user_dir)):
            u = user_data.User_data(self.image_list, user_dir[i], self, grades_p[i], grades_t[i])
            self.user_list.append(u)
            self.nb_users += 1
        for image in self.image_list:
            image.init_user_data_link(self.user_list)

    def __repr__(self):
        return "NbIm : " + str(self.nb_images) + ", NbUsers : " + str(self.nb_users) + "\n"

    def __str__(self):
        return "NbIm : " + str(self.nb_images) + ", NbUsers : " + str( self.nb_users) + "\n"

    def nb_users(self):
        return self.nb_users

    def nb_images(self):
        return self.nb_images

    def add_user_id(self, out):
        out.append(['User ID'])
        for i in range(len(self.user_list)):
            out.append([self.user_list[i].user_id])
        return out

    def var1_nb_im_visited(self, out):
        out[0].append('Nb Images Visited')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].nb_ims_visited())
        return out

    def var2_total_nb_positions(self, out):
        out[0].append('Total Nb Positions')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].total_nb_positions())
        return out

    def var3_average_nb_positions(self, out):
        out[0].append('Avg Nb Positions')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].avg_nb_positions_visited())
        return out

    def var4_median_nb_positions(self, out):
        out[0].append('Median Nb Positions')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].median_nb_positions())
        return out

    def var5_total_time(self, out):
        out[0].append('Total Image Viewing Time (s)')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].total_time_spent())
        return out

    def var6_avg_time(self, out):
        out[0].append('Average Image Viewing Time (s)')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].avg_time_spent())
        return out

    def var7_median_time(self, out):
        out[0].append('Median Image Viewing Time (s)')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].median_time_spent())
        return out

    def var8_position_zooms(self, out):
        for i in range(config.MAX_ZOOM):
            out[0].append('Nb Positions at zoom ' + str(i + 1))

        for i in range(len(self.user_list)):
            array = self.user_list[i].zoom_position_number()
            for j in range(len(array)):
                out[i + 1].append(array[j])
        return out

    def var9_avg_position_zooms(self, out):
        out[0].append('Average Zoom')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].zoom_position_avg())
        return out

    def var10_median_position_zooms(self, out):
        out[0].append('Median Zoom')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].zoom_position_median())
        return out

    def var11_total_annotation_actions(self, out):
        out[0].append('Total AnnotationActions')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].total_annotation_actions())
        return out

    def var12_avg_annotation_actions(self, out):
        out[0].append('Avg AnnotationActions')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].avg_annotation_actions())
        return out

    def var13_median_annotation_actions(self, out):
        out[0].append('Median AnnotationActions')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].median_annotation_actions())
        return out

    def var_results(self, out):
        out[0].append('Theory Results')
        out[0].append('Practical Results')
        for i in range(len(self.user_list)):
            out[i + 1].append(self.user_list[i].get_grade_theory())
            out[i + 1].append(self.user_list[i].get_grade_practical())
        return out


    def write_ml_csv(self):
        out = []
        csv_out_filename = 'learning_data.csv'
        stats_file = os.path.join(config.WORKING_DIRECTORY + self.project_name + "/",
                                  csv_out_filename)
        f = open(stats_file, "wb")
        csv_out = csv.writer(f)

        self.add_user_id(out)
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


        self.var_results(out)

        csv_out.writerow(out[0])
        for i in range(len(self.user_list)):
            csv_out.writerow(out[i + 1])

        f.close()

    def write_gazemaps(self):
        for image in self.image_list:
            #todo : only 1217722 atm
            #if image.image_id == "1217722":
                image.generate_all_heatmaps()
                image.save_all_heatmaps()
                image.save_all_heatmaps_ln()
                image.save_all_heatmaps_by_image()
                image.save_all_raw()
                image.save_all_scanpath()
                image.remove_all_heatmaps()
                print str(image.image_id)+ "test\n"
                gc.collect()

        for user in self.user_list:
            #todo : only 3425935 atm
            #if user.user_id == "3425935":
                for im_id in user.image_data:
                    image = user.image_data[im_id]
                    image.generate_heatmap(user.user_id)
                user.save_all_heatmaps_by_user()
                for im_id in user.image_data:
                    image = user.image_data[im_id]
                    image.remove_heatmap(user.user_id)
                gc.collect()


if __name__ == '__main__':

    if len(sys.argv) != 2:
        print "Format: image_data.py <project_name>"
    else:
        manager = Data_manager(sys.argv[1])
        print manager
        print "Generating ML data..."
        manager.write_ml_csv()
        print "Generating Gazemaps..."
        manager.write_gazemaps()

