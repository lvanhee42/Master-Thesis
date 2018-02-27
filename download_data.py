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

##TODO : add ConnectionHistory to python client and use it

#local
cytomine_host=config.cytomine_host
cytomine_public_key= config.cytomine_public_key
cytomine_private_key= config.cytomine_private_key


#Connection to Cytomine Core
conn = Cytomine(cytomine_host, cytomine_public_key, cytomine_private_key, base_path = '/api/', working_path = '/tmp/', verbose= False)

rescaled_size = 1024
working_path = config.WORKING_DIRECTORY  # directory should exist

radius = 10  # 20 for 2048 images, 10 for 1024
frequency = 1
video = False
timefig = False
zoomfig = False
maxperpage = 500  # unamur
tolerated_distance = 400
opening_delay = 10000  # 10s

timestep = 86400  # 1 day (in seconds)

id_user = 27389949  # DEMO-LANDMARK-ZEBRAFISH
start_time = "2016-09-09 21:00:00"
end_time = "2018-06-13 19:30:00"
#id_ref_user = 1590 # gold
id_ref_user = 1611 # silver

id_project=2338 #silver
#id_project = 1197608  # gold
# id_ref_user=1611  #moochistos


#project_dir = "gold/"
project_dir = "silver/"
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

# imagelist to exclude
# silver_image_list = [26731545,26731493,26670840,26670834,1054646,1008030,990429,974081,953615,953461,935691,872673,872563,870411,870405,865730,865636,865563,368660,265174,219925,207190,206610,206366,135106,25025,8801,8795,8789,6324,6198,6150,6062,5976,5294,5240,5182,5140,5034,4990,4944,4896,4852,4807,4582,4540,4454,4412,4304,4260,4218,4172,4122,4072,4018,3961,3879,3827,3783,3711,3667,3625,3543,3453,3411,3104,3060,3014,2964,2911,2867,2813,2762,2724]  # removed: 3499
# gold_image_list = [26731296 26707997 26670588 26670368 23406419 1552356 1227247 1219597 1219330 1219137 1218942 1218931 1218920 1218727 1218530 1218337 1218326 1218315 1218120 1217927 1217722 1217514 1217333 1217031 1216821 1216615 1216530 1216341 1215703 1215303 1214613 1213901 1213647 1213537 1213401 1213003 1212431 1211767 1210909 1210872 1210326 1210048 1209840 1209728 1209160 1208906 1208312 1208248 1208042 1207786 1207266 1206962 1206852 1206138 1205882 1205626 1205396 1205188 1205177 1204731 1204545 1204337 1203529 1203177 1202969 1202279 1202049 1201577 1201225 1201017 1200739 1200409 1200227 1199971 1199065 1198335 1198322 1197634]
# gold_image_list_ex = [26731296,26707997,26670588,26670368,23406419,1552356,1227247,1219597,1219330,1219137,1218942,1218931,1218920,1218727,1218530,1218337,1218326,1218315,1218120,1217927,1217722,1217514,1217333,1217031,1216821,1216615,1216530,1216341,1215703,1215303,1214613,1213901,1213647,1213537,1213401,1213003,1212431,1211767,1210909,1210872,1210326,1210048,1209840,1209728,1209160,1208906,1208312,1208248,1208042,1207786,1207266,1206962,1206852,1206138,1205882,1205626,1205396,1205188,1205177,1204731,1204545,1204337]


# imagelist_ex = silver_image_list
# imagelist_ex = gold_image_list_ex
imagelist_ex = []

# for image in images:
#    print image.id
# time.sleep(10)


# mooc gold full imagelist
# 26731545 26731493 26670840 26670834 1054646 1008030 990429 974081 953615 953461 935691 872673 872563 870411 870405 865730 865636 865563 368660 265174 219925 207190 206610 206366 135106 25025 8801 8795 8789 6324 6198 6150 6062 5976 5294 5240 5182 5140 5034 4990 4944 4896 4852 4807 4582 4540 4454 4412 4304 4260 4218 4172 4122 4072 4018 3961 3879 3827 3783 3711 3667 3625 3543 3499 3453 3411 3104 3060 3014 2964 2911 2867 2813 2762 2724

# users to include

silver_list = [5953797, 5815144, 4485740, 3634514, 3640131, 5135717, 1724450, 2130390, 3782245, 4101145, 3344084,
               2882254, 1845212, 2172095, 5341408, 6997659, 2945656, 24095526, 6276744, 1971674, 5759043, 11743326,
               1877468, 4315757, 5622155, 1793969, 3443679, 2891182, 5750494, 1957066, 1807583, 4609133, 6262043,
               5270874, 1847015, 1936219, 2899917, 3569433, 4053729, 1961697, 1946117, 5444792, 4910612, 3030833,
               5213990, 1730146, 6002923, 3106845, 2553352, 5567960, 5389906, 5638247, 1981506, 2826352, 1976597,
               2179399, 2516121, 1984669, 2155987, 5541256, 5442074, 2685092, 5601562, 2052408, 3588362, 2053658,
               4386888, 5884256, 7365497, 4370202, 2805582, 5980124, 2052195, 2111818, 2155678, 5650725, 4538258,
               1728825, 2456991, 2392293, 1766842, 2056227, 7250737, 2076489, 1954356]
gold_list = [13835466, 6075155, 13263823, 3640131, 13761151, 7037470, 2822865, 2867968, 19482108, 1736248, 1909811,
             18707558, 1797649, 3530049, 7341348, 3260578, 3949307, 5183006, 7008441, 15083231, 12826956, 4711196,
             12598218, 4280733, 6775281, 3347952, 4632353, 3982533, 25787007, 10366353, 4422257, 6039699, 19842784,
             17841388, 6782899, 19199658, 3180914, 19510675, 2261567, 19069082, 15152190, 1723723, 25578776, 7306777,
             2107723, 2330432, 24128267, 2426961, 23108473, 1794782, 12955025, 6810056, 2195398, 5218258, 16207087,
             2447623, 2547321, 7621674, 11568529, 6964233, 6494768, 5716865, 9843370, 2322062, 1813443, 13362438,
             8421500, 19528357, 1818247, 6174022, 2356110, 2851162, 1874622, 3824389, 2406344, 1920453, 5435489,
             4282396, 4751667, 4915259, 9949326, 5044427, 2246960, 2172207, 1790499, 7365497, 7054060, 5272396, 9310207,
             7473762, 3264564, 6812034, 2968719, 8923296, 2538677, 2248593, 3534208, 5769449, 6554783, 23637567,
             1804121, 2467790, 13785156, 25618424, 8059104, 4452008, 7695190, 2380106, 4094628, 7877557, 3940644,
             2811987, 1741659, 2289488]

gold_ULG_list = [3469686, 5953797, 3664849, 5815144, 6225566, 4485740, 1949128, 3634514, 4540861, 3640131, 3258785,
                 2103379, 5135717, 2928977, 6080033, 1756092, 2919700, 2022736, 2946467, 1724450, 2007660, 4176976,
                 2130390, 1750971, 2849577, 6765717, 2497287, 3402191, 5685265, 5501147, 3782245, 3828994, 2127339,
                 4317813, 4101145, 4035896, 4229057, 3905979, 4052263, 1931337, 5424912, 4437233, 3344084, 3171328,
                 2384402, 5517908, 2882254, 2566057, 1845212, 6380587, 11310260, 2172095, 24208856, 1842488, 4136832,
                 5341408, 5650995, 6226684, 6997659, 4592450, 3035834, 1993524, 1990393, 5762800, 6525820, 2945656,
                 5924525, 1734247, 2551747, 24095526, 1926338, 2498280, 1804374, 3231712, 6276744, 1971674, 5730056,
                 4371893, 3683534, 1879987, 5759043, 11743326, 2161758, 1877468, 3018759, 4315757, 5622155, 2880747,
                 2026631, 6164830, 1793969, 3427574, 3443679, 2040409, 2891182, 6538122, 4274533, 2021313, 2163591,
                 5617039, 4155259, 4741739, 3194598, 5110412, 6922933, 2017285, 2108805, 3408166, 6525835, 5213445,
                 3367859, 5750494, 6754144, 2117699, 2071954, 3639597, 3554348, 1957066, 2244448, 2375005, 5111725,
                 1987587, 2823912, 5352807, 1807583, 4609133, 4310497, 1985698, 12055926, 5322115, 6262043, 4328563,
                 16346219, 5270874, 2577486, 5652785, 1972810, 6220926, 2073764, 3256881, 1847015, 4174176, 1936219,
                 2899917, 3569433, 1839051, 5724953, 4053729, 3755674, 1914037, 5901786, 6021609, 4540338, 2110121,
                 6048193, 1925768, 6162294, 2989493, 4188329, 2767221, 1961697, 1946117, 6364679, 6495701, 1974891,
                 5444792, 4450578, 2409720, 2048270, 3082366, 3575161, 3514323, 4280616, 4620458, 4945683, 4910612,
                 3030833, 5213990, 4363366, 5692988, 1730146, 4249164, 11968796, 4723109, 2926083, 3001654, 4760698,
                 1982524, 6002923, 1947998, 4819050, 1975815, 3106845, 4377154, 2553352, 5567960, 1948553, 3038222,
                 5389906, 5638247, 2645248, 3666692, 2135994, 13132480, 1981506, 3047790, 2007551, 3520363, 4399492,
                 5552971, 4748491, 5255027, 5742394, 2119699, 5517940, 2109296, 3374976, 5882824, 4582853, 2774839,
                 4240983, 3338708, 6253305, 2826352, 1976597, 2028244, 2179399, 2516121, 6766156, 4580663, 6305009,
                 4595201, 3209844, 1947770, 1984669, 4869953, 6457633, 1795356, 2155987, 5541256, 2582554, 4589371,
                 5690878, 5442074, 3879700, 2539878, 2685092, 5601562, 3647333, 4873862, 2486640, 3097420, 3513967,
                 4422652, 5188023, 1938021, 1726163, 6420595, 5861452, 2052408, 5243824, 4654399, 2732662, 2890068,
                 3588362, 3690231, 3577073, 3789823, 4321998, 3494635, 6331753, 5743146, 5324499, 2053658, 4386888,
                 5884256, 2113018, 2250414, 5431885, 2983730, 3713496, 5897419, 2618268, 3719043, 3488084, 2043279,
                 2170410, 2144210, 3835785, 1942114, 4370202, 2805582, 4331187, 5980124, 6215976, 3064978, 3248377,
                 1995352, 3157492, 6607811, 4659849, 5352682, 1757228, 2561363, 2052195, 2061069, 6018416, 4694828,
                 2111818, 3676409, 5760595, 2155678, 2435618, 6423254, 6477227, 15890809, 1729776, 5650725, 4538258,
                 1728825, 2456991, 4874141, 2114511, 2392293, 4236332, 5890545, 2599108, 1942732, 2728461, 1824486,
                 5664760, 2500799, 2146924, 5030048, 4295208, 2578358, 1766842, 5078270, 2903912, 2056227, 7250737,
                 5495643, 1729177, 3115460, 1984925, 1747564, 5605333, 1985273, 3425935, 2076489, 3228621, 1832142,
                 1919724, 1758853, 2278108, 4589554, 1954356, 5216320]


demo_landmark_zebrafish_list = [28, 33, 35, 37]
# anapath_list = [24768144]


# demo images [4269,4163,4057,3951,3845,3739,3699,3659,3553,3513,3473,3367,3261,3221,3181,3141,3101,2995,2889,2783,2677,2571,2465,2359,2319,2213,2107,2001,1895,1789]

#userlist = gold_ULG_list
#userlist = gold_list
# userlist = silver_list
# userlist = anapath_list
# userlist = demo_landmark_zebrafish_list


if not os.path.exists(working_path + project_dir + "images/"):
    os.makedirs(working_path + project_dir + "images/")

# Create user id file
csv_user_filename = 'users.csv'
users_file = os.path.join(working_path + project_dir, csv_user_filename)
copyfile("stats/students_silver.csv", users_file)

fusers = open("stats/students_silver.csv", "rb")
csvoutusers = csv.reader(fusers)
data_users = list(csvoutusers)
data_users.pop(0)
userlist = []
for u_tmp in data_users:
    userlist.append(int(u_tmp[0]))
fusers.close()

#Go through all images
for image in images:
    id_image=image.id
    print "Downloading data associated to image %d" %id_image
    if id_image in imagelist_ex:
        print "Image %d already analyzed" %id_image
    else:
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
                                                   showWKT=True)
            nb_ref_annotations = len(ref_annotations.data())
        else:
            ref_annotations = None
            nb_ref_annotations = 0
        #save the center of the reference annotations in a csv file
        csv_filename = 'reference_cytomine_annotations.csv'
        if nb_ref_annotations > 0:
            output_annotation_file = os.path.join(working_path + project_dir + image_dir + "/", csv_filename)
            f = open(output_annotation_file, "wb")
            csv_annotations = csv.writer(f)
            csv_annotations.writerow(['type', 'x_center', 'y_center', 'annotationIdent'])
            for a in ref_annotations.data():
                geom = loads(a.location)
                if geom.type == 'Point':
                    csv_annotations.writerow([geom.type, round(geom.x / rescale_factor), round(geom.y / rescale_factor), a.id])
                else:
                    csv_annotations.writerow([geom.type, round(geom.centroid.x / rescale_factor), round(geom.centroid.y / rescale_factor), a.id])
            f.close()

        # for this image, go through project's users (except those not in provided userlist)
        for u in id_users.data():
            if u.id in userlist:

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
                            nb_filtered_annotations+=1
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
