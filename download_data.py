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


__author__          = "Vanhee Laurent (and Marée Raphaël) <laurent.vanhee@student.uliege.ac.be>"
__copyright__       = "Copyright 2010-2017 University of Liège, Belgium, http://www.cytomine.be/"


import csv
import datetime
import math
import os
import socket
import time
import numpy as np
from cytomine.models import *
from shapely.wkt import loads
from shutil import copyfile
import config
from cytomine import Cytomine
from PIL import Image
import sys
import inspect
##TODO : add ConnectionHistory to python client and use it


def get_data(project_dir, id_project, users_metadata_file, id_ref_user, im_subset=None, us_subset=None,
             cytomine_host=config.cytomine_host, cytomine_public_key=config.cytomine_public_key,
             cytomine_private_key=config.cytomine_private_key, modules=None):
    """

    :param project_dir: gold, silver
    :param id_project: 2338 -> silver, 1197608-> gold
    :param users_metadata_file: stats/students_gold.csv, stats/students_silver.csv
    :param id_ref_user : 1590 -> gold, 1611 -> silver
    :param im_subset : optional, makes script only fetch info on a subset of images
    :param us_subset : optional, makes script only fetch info on a subset of users
    :param cytomine_host: optional, Cytomine host address
    :param cytomine_private_key: optional, Cytomine user private key
    :param cytomine_public_key: optional, Cytomine user public key
    :param modules: optional, file directory containing modules
    :return:
    """


    #Connection to Cytomine Core
    conn = Cytomine(cytomine_host, cytomine_public_key, cytomine_private_key, base_path = '/api/', working_path = '/tmp/', verbose= False)

    rescaled_size = 1024
    working_path = config.WORKING_DIRECTORY  # directory should exist

    maxperpage = 500  # unamur
    opening_delay = 10000  # 10s

    timestep = 86400  # 1 day (in seconds)

    id_user = 27389949  # DEMO-LANDMARK-ZEBRAFISH
    start_time = config.start_time
    end_time = config.end_time


    if '/' not in project_dir:
        project_dir = project_dir + "/"
    # --------------------------------------------------------------------------------------
    # --------------------------------------------------------------------------------------
    if not os.path.exists(working_path + project_dir):
        os.makedirs(working_path + project_dir)


    # We convert start/end string time to python timestamps (multiply by 1000 as python expects seconds)
    start_timestamp = long(1000 * time.mktime(datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").timetuple()))
    end_timestamp = long(1000 * time.mktime(datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").timetuple()))


    # Create project stats file
    csv_stats_filename = 'stats.csv'
    stats_file = os.path.join(working_path + project_dir, csv_stats_filename)
    fstats = open(stats_file, "wb")
    csvoutstats = csv.writer(fstats)
    csvoutstats.writerow([start_timestamp, end_timestamp])
    csvoutstats.writerow(
        ['id_project', 'id_image', 'id_user', 'username', 'email', 'nb_user_annotations', 'central_positions_nb_opens',
         'nb_positions', 'zoom_frequencies', 'nb_reference_points'])

    # Get all project users:
    id_users = conn.get_project_users(id_project)  # of from arglist

    # Get all image instances from project
    # Here we should check arg, if null then get all images from project
    image_instances = ImageInstanceCollection()
    image_instances.project = id_project
    image_instances = conn.fetch(image_instances)
    images = image_instances.data()
    print "Nb images in project: %d" % len(images)



    if not os.path.exists(working_path + project_dir + "images/"):
        os.makedirs(working_path + project_dir + "images/")


    # Create user id file
    if modules is not None:
        csv_user_filename = 'timeline.csv'
        modules_file = os.path.join(working_path + project_dir, csv_user_filename)
        copyfile(modules, modules_file)

    # Create user id file
    csv_user_filename = 'users.csv'
    users_file = os.path.join(working_path + project_dir, csv_user_filename)
    copyfile(users_metadata_file, users_file)

    fusers = open(users_metadata_file, "rb")
    csvoutusers = csv.reader(fusers)
    data_users = list(csvoutusers)
    data_users.pop(0)
    header = data_users.pop(0)
    user_idx = 0
    for i in range(len(header)):
        if header[i] == "CYTOMINE ID":
            user_idx = i
    userlist = []
    print user_idx
    for u_tmp in data_users:
        userlist.append(int(u_tmp[user_idx]))
    fusers.close()

    if im_subset is None:
        im_subset = []
        for image in images:
            im_subset.append(image.id)

    #Go through all images
    for image in images:
        id_image=image.id
        print "Downloading data associated to image %d" %id_image
        if id_image in im_subset:
            image_dir = "images/image_" + str(id_image)
            if not os.path.exists(working_path + project_dir + image_dir):
                os.makedirs(working_path + project_dir + image_dir)

            #get abstractimage thumb, compute rescaling factor (original image size / thumb size)
            image_instance = conn.get_image_instance(id_image)
            max_dim = max(image_instance.height,image_instance.width)
            image_depth = image_instance.depth
            if max_dim>rescaled_size:
                rescale_factor = max_dim/rescaled_size
            else:
                rescale_factor=1

            url = image_instance.preview[0:image_instance.preview.index('?')] + "?maxSize=" + str(rescaled_size)
            filename = working_path + project_dir + image_dir + "/image.png"
            if not os.path.exists(filename):
                conn.fetch_url_into_file(url, filename, override=True)

            rescaled_im = Image.open(filename)
            rescaled_width, rescaled_height = rescaled_im.size

            # Get reference annotations in this image (to detect if reference regions were visualized by user)
            nb_ref_annotations = 0
            if id_ref_user:
                ref_annotations = conn.get_annotations(id_image=id_image,
                                                       id_user=id_ref_user,
                                                       id_project=id_project,
                                                       showWKT=True
                                                       )
                nb_ref_annotations = len(ref_annotations.data())
            else:
                ref_annotations = None
            #save the center of the reference annotations in a csv file
            csv_filename = 'reference_cytomine_annotations.csv'
            if nb_ref_annotations > 0:

                output_annotation_file = os.path.join(working_path + project_dir + image_dir + "/", csv_filename)
                f = open(output_annotation_file, "wb")
                csv_annotations = csv.writer(f)
                csv_annotations.writerow(['type', 'x_center', 'y_center', 'annotationIdent', 'localIdent'])
                for a in ref_annotations.data():

                    descr = conn.get_annotation_properties(a.id)
                    l_id = 0
                    for prop in descr.data():
                        if prop.key == 'n':
                            l_id = prop.value


                    geom = loads(a.location)

                    if geom.type == 'Point':
                        csv_annotations.writerow([geom.type, round(geom.x / rescale_factor), round(geom.y / rescale_factor), a.id, l_id])
                    else:
                        csv_annotations.writerow([geom.type, round(geom.centroid.x / rescale_factor), round(geom.centroid.y / rescale_factor), a.id, l_id])
                f.close()

            # for this image, go through project's users (except those not in provided userlist)
            for u in id_users.data():
                if u.id in userlist and (us_subset is None or u.id in us_subset ):

                    zooms = np.zeros(image_instance.depth)
                    id_user = u.id
                    if not os.path.exists(working_path + project_dir + image_dir + "/user_positions"):
                        os.makedirs(working_path + project_dir +  image_dir + "/user_positions")
                    # Get_positions for this user in this image: using paging (maxperpage) and using start/end timestamps
                    pos_success = False
                    while (not pos_success):
                        # Retry if we got error
                        try:
                            positions = conn.get_positions(id_image=id_image,
                                                           id_user=id_user,
                                                           maxperpage=maxperpage,
                                                           afterthan=start_timestamp,
                                                           beforethan=end_timestamp,
                                                           showDetails=True)
                            pos_success = True
                        except socket.error:
                            print socket.error
                            time.sleep(1)
                            continue
                        except socket.timeout:
                            print socket.timeout
                            time.sleep(1)
                            continue
                        except ValueError:
                            print socket.timeout
                            time.sleep(1)
                            continue
                        except Exception:
                            time.sleep(1)
                            continue

                    nb_positions = len(positions.data())
                    nb_opens = 0
                    if nb_positions == 0:
                        fstats.flush()
                    elif nb_positions > 0:
                        csv_filename = str(id_user) + "_" + str(u.username) + '_cytomine_positions.csv'
                        #create output csv file to store positions
                        output_position_file = os.path.join(working_path + project_dir + image_dir + "/user_positions" , csv_filename)
                        f = open(output_position_file, "wb")
                        csvout = csv.writer(f)

                        #Create vector for distribution of zoom levels
                        #Create vector for distribution of days (end_time - start_time)
                        nb_time_intervals = int(math.ceil((end_timestamp-start_timestamp)/timestep))/1000
                        time_intervals = np.zeros(nb_time_intervals+1)
                        central_positions = np.zeros(nb_time_intervals+1)

                        #Filter obtained positions based on start/end timestamp (only write in csv positions included in the given time interval)
                        #Save every position in a csv file
                        previous_central=float(start_timestamp)
                        csvout.writerow(['corners', 'center', 'zoom', 'created'])
                        for p in positions.data():
                            if float(p.created) > float(start_timestamp) and float(p.created) < float(end_timestamp):

                                in_timeinterval = int(math.floor((float(p.created) - float(start_timestamp)) / timestep)) / 1000
                                geom = loads(p.location)
                                if (p.x != image_instance.width / 2) and (p.y != image_instance.height / 2):
                                    rescaled_corners = list(geom.exterior.coords)
                                    rescaled_corners.pop()
                                    rescaled_corners = [tuple(map(lambda divide : round(divide / rescale_factor), corner)) for corner in rescaled_corners]
                                    #csvout.writerow([list(geom.exterior.coords),(int(round(p.x / rescale_factor)), int(round(p.y / rescale_factor))), int(p.zoom), float(p.created)])
                                    csvout.writerow([rescaled_corners, (round(geom.centroid.x / rescale_factor), round(geom.centroid.y / rescale_factor)), int(p.zoom), float(p.created)])
                                    zooms[p.zoom - 1] += 1
                                    time_intervals[in_timeinterval] += 1
                                else:
                                    central_positions[in_timeinterval] += 1
                                    if float(p.created) - previous_central > opening_delay:  # if > 10s we assume user opens the image again
                                        nb_opens += 1
                                    previous_central = float(p.created)
                            else:
                                print "Point removed because not in the timeframe"  # should not happen

                        f.close()

                    #Get Annotations
                    #Get user annotations in this image (to generate statistics about annotation creation).
                    nb_filtered_annotations=0
                    annotations = conn.get_annotations(id_image=id_image,
                                                       id_user=id_user,
                                                       id_project=id_project)
                    nb_annotations = len(annotations.data())
                    csv_filename = str(id_user) + "_" + str(u.username) + '_cytomine_annotations.csv'
                    if not os.path.exists(working_path + project_dir + image_dir + "/user_annotations"):
                        os.makedirs(working_path + project_dir + image_dir + "/user_annotations")
                    if nb_annotations > 0:
                        print "We actually have at least 1 annotation"
                        output_annotation_file = os.path.join(working_path + project_dir + image_dir + "/user_annotations", csv_filename)
                        f = open(output_annotation_file, "wb")
                        csv_annotations = csv.writer(f)
                        csv_annotations.writerow(['type', 'x_center', 'y_center', 'annotationIdent'])
                        for a in annotations.data():
                            if float(a.created) > float(start_timestamp) and float(a.created) < float(end_timestamp):
                                geom = loads(a.location)
                                nb_filtered_annotations += 1
                                if geom.type == 'Point':
                                    csv_annotations.writerow([geom.type,geom.x,geom.y,a.id])
                                else:
                                    csv_annotations.writerow([geom.type, geom.centroid.x, geom.centroid.y,a.id])
                        f.close()

                    #Get AnnotationActions
                    if not os.path.exists(working_path + project_dir + image_dir + "/user_actions"):
                        os.makedirs(working_path + project_dir + image_dir + "/user_actions")
                    pos_success = False
                    while (not pos_success):
                        # Retry if we got error
                        try:
                            ann_actions = conn.get_annoationactions(id_image=id_image,
                                                           id_user=id_user,
                                                           maxperpage=maxperpage,
                                                           afterthan=start_timestamp,
                                                           beforethan=end_timestamp,
                                                           showDetails=True)
                            pos_success = True
                        except socket.error:
                            print socket.error
                            time.sleep(1)
                            continue
                        except socket.timeout:
                            print socket.timeout
                            time.sleep(1)
                            continue
                        except ValueError:
                            print socket.timeout
                            time.sleep(1)
                            continue
                        except Exception:
                            time.sleep(1)
                            continue
                    nb_actions = len(ann_actions.data())
                    if nb_actions == 0:
                        fstats.flush()
                    elif nb_actions > 0:
                        csv_filename = str(id_user) + "_" + str(u.username) + '_cytomine_actions.csv'
                        #create output csv file to store actions
                        output_action_file = os.path.join(working_path + project_dir + image_dir + "/user_actions" , csv_filename)
                        f = open(output_action_file, "wb")
                        csvout = csv.writer(f)

                        #Create vector for distribution of zoom levels
                        #Create vector for distribution of days (end_time - start_time)
                        nb_time_intervals = int(math.ceil((end_timestamp-start_timestamp)/timestep))/1000
                        time_intervals = np.zeros(nb_time_intervals+1)
                        central_positions = np.zeros(nb_time_intervals+1)

                        #Filter obtained positions based on start/end timestamp (only write in csv positions included in the given time interval)
                        #Save every position in a csv file
                        previous_central=float(start_timestamp)
                        csvout.writerow(['annotationIdent', 'created', 'action'])
                        for a in ann_actions.data():
                            if float(a.created) > float(start_timestamp) and float(a.created) < float(end_timestamp):
                                csvout.writerow([a.annotationIdent, a.created, a.action])
                        f.close()


                    csvoutstats.writerow(
                        [id_project, id_image, id_user, u.username, u.email, nb_annotations, nb_opens, sum(zooms), zooms,
                         nb_ref_annotations])


def handle_args(args):

    users = False
    user_info = None
    pub_key = config.cytomine_public_key
    priv_key = config.cytomine_private_key
    host = config.cytomine_host
    images = False
    image_info = None
    modules = None
    try:
        name = str(args[1])
        id_proj = int(args[2])
        users_files = str(args[3])
        ref_user = int(args[4])

        i = 5
        while i < len(args):
            if args[i] == "-U" and (i + 1) < len(args):
                users = True
                user_info = str(args[i + 1])
                i += 2
            elif args[i] == "-I" and (i + 1) < len(args):
                images = True
                image_info = str(args[i + 1])
                i += 2
            elif args[i] == "-PR" and (i + 1) < len(args):
                priv_key = str(args[i + 1])
                i += 2
            elif args[i] == "-PU" and (i + 1) < len(args):
                pub_key = str(args[i + 1])
                i += 2
            elif args[i] == "-H" and (i + 1) < len(args):
                host = str(args[i + 1])
                i += 2
            elif args[i] == "-M" and (i + 1) < len(args):
                modules = str(args[i + 1])
                i += 2

    except:
        error_msg()
        return

    image_list = None
    if images is True:
        f_image_list = open(image_info, "rb")
        csv_in = csv.reader(f_image_list)
        data_im = list(csv_in)
        image_list = []
        for i_tmp in data_im:
            image_list.append(str(i_tmp[0]))
        f_image_list.close()

    user_list = None
    if users is True:
        f_user_list = open(user_info, 'rb')
        csv_in = csv.reader(f_user_list)
        data_user = list(csv_in)
        user_list = []
        for u_tmp in data_user:
            user_list.append(str(u_tmp[0]))
        f_user_list.close()

    get_data(name, id_proj, users_files, ref_user, im_subset=image_list, us_subset=user_list, cytomine_host=host, cytomine_private_key=priv_key,
             cytomine_public_key=pub_key, modules=modules)



def error_msg():
    """
    Output error msg
    :return:
    """

    print "Format : download_data.py <project_name> <project_id> <users_file> <ref_user_id>"
    print "Options (-I and -U uses default settings if not specified):"
    print "  -H <host>:\n    The Cytomine host address\n"
    print "  -PR <cytomine_pr_key>\n    The user's Cytomine private key"
    print "  -PU <cytomine_pu_key>\n    The user's Cytomine public key"
    print "  -I <image_id_file_dir> :\n    CSV file with image IDs, Default takes all images in the project\n    Gets data on the subset of images\n"
    print "  -U <user_id file_dir> :\n    CSV file with user IDs, Default takes all the users in the users metadata file\n    Gets data on the subset of users\n"
    print "  -/m <module file_dir> :\n    CSV file with moduless, Default no modules\n    copies this file\n"


if __name__ == '__main__':

    handle_args(sys.argv)
