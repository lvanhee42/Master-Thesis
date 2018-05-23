from datetime import datetime
import time
import config
from gazemap import score_user_on_image

class Module_data:
    """
    This class represents information on a module.
    It includes operations to draw statistics from this module
    """
    def __init__(self, file_row, image_list, data_manager, user_list):

        self.data_manager = data_manager

        self.id = file_row[0]
        self.start_date = datetime.strptime(file_row[1] + " 00:00", "%d/%m/%Y %H:%M")
        self.end_date = datetime.strptime(file_row[2] + " 23:59", "%d/%m/%Y %H:%M")
        self.start = long(1000 * time.mktime(datetime.strptime(file_row[1] + " 00:00", "%d/%m/%Y %H:%M").timetuple()))
        self.end = long(1000 * time.mktime(datetime.strptime(file_row[2] + " 23:59", "%d/%m/%Y %H:%M").timetuple()))
        self.images = {}
        self.types = {}
        self.user_list = user_list

        i = 3
        while i + 1 < len(file_row) and file_row[i] != "":
            im_id = file_row[i]
            im_type = file_row[i + 1]

            for j in range(len(image_list)):
                if im_id == image_list[j].image_id:
                    self.images[im_id] = image_list[j]
                    self.types[im_id] = im_type
                    break

            i += 2

    def start_end_indexes(self, positions):
        """
        Binary search to find the positions in our time range
        :param positions: Position dictionary
        :return:start idx, end idx
        """
        array = positions['timestamp']
        if len(array) == 0:
            return 0, -1
        minIt = 0
        maxIt = len(array) - 1
        i = int(len(array)/2)
        start = 0
        end = 0
        # exit when array[i -1] < self.start <= array[i]
        while array[i] != self.start:
            previ = i
            if array[i] < self.start:
                minIt = i
                i = int((i + maxIt)/2)
            else:
                maxIt = i
                i = int((i + minIt)/2)

            if previ == i:
                if array[i] < self.start:
                    start = i + 1
                else:
                    start = i
                break
        minIt = 0
        maxIt = len(array) - 1
        i = int(len(array)/2)
        while array[i] != self.end:
            previ = i
            if array[i] < self.end:
                minIt = i
                i = int((i + maxIt) / 2)
            else:
                maxIt = i
                i = int((i + minIt) / 2)

            if previ == i:
                if array[i] > self.end:
                    end = i - 1
                else:
                    end = i
                break

        return max(start, 0), min(end, len(array) - 1)


    def nb_positions_total_avg_median(self):
        """
        calculates position variables for each user
        :return: 1) total
                 2) average
                 3) median
                 4) nb of images visited
        """
        ret = []
        ret2 = []
        ret3 = []
        ret4 = []
        for user in self.user_list:
            nb = 0
            nb_im = 0
            med_list = []
            for image_id in self.images:
                if image_id in user.positions:
                    pos = user.positions[image_id]
                    start, end = self.start_end_indexes(pos)
                    nb += end - start + 1
                    med_list.append(end - start + 1)
                    if end > start:
                        nb_im += 1
                else:
                    med_list.append(0)

            ret.append(nb)
            if len(self.images) == 0:
                ret2.append(0)
            else:
                ret2.append(float(nb)/len(self.images))
            med_list.sort()
            if len(med_list) == 0:
                ret3.append(0)
            else:
                ret3.append(med_list[int(len(med_list)/2)])
            ret4.append(nb_im)

        return ret, ret2, ret3, ret4

    def time_spent_total_avg_median(self):
        """
        calculates time spent variables for each user
        :return: 1) total
                 2) average
                 3) median
        """
        ret = []
        ret2 = []
        ret3 = []
        for user in self.user_list:
            tot = 0.0
            med_list = []
            for image_id in self.images:
                time = self.time_spent(image_id, user)
                tot += time
                med_list.append(time)

            med_list.sort()
            ret.append(tot)
            if len(self.images) == 0:
                ret2.append(0)
            else:
                ret2.append(float(tot)/len(self.images))
            if len(med_list) == 0:
                ret3.append(0)
            else:
                ret3.append(med_list[int(len(med_list)/2)])

        return ret, ret2, ret3



    def time_spent(self, im_id, user):
        """
        Calculates total time spent on an image
        :param im_id: image id
        :param user: User_data object
        :return: time in seconds
        """
        if im_id not in user.positions:
            return 0.0

        positions = user.positions[im_id]
        start, end = self.start_end_indexes(positions)
        if end <= start:
            return 0.0
        timestamps = positions['timestamp']
        i = start + 1
        time_on_image = 0.0
        while i <= end:
            ## timestamps are spaced at a interval of a maximum 5000ms
            if timestamps[i] - timestamps[i - 1] < 6000:
                time_on_image += timestamps[i] - timestamps[i - 1]
                i += 1
            else:
                i += 2
        return time_on_image / 1000.0

    def zooms(self):
        ret = []
        ret2 = []
        ret3 = [[] for j in range(config.MAX_ZOOM)]
        ret4 = [[] for j in range(config.MAX_ZOOM)]
        ret5 = [[] for j in range(config.MAX_ZOOM)]
        for user in self.user_list:
            tot = 0
            nb = 0
            med_list = []
            tot_per_zoom = [0 for j in range(config.MAX_ZOOM)]
            avg_per_zoom = [0 for j in range(config.MAX_ZOOM)]
            med_per_zoom = [[] for j in range(config.MAX_ZOOM)]
            for image_id in self.images:
                if image_id in user.positions:
                    pos = user.positions[image_id]
                    start, end = self.start_end_indexes(pos)
                    nb_per_image = [0 for j in range(config.MAX_ZOOM)]
                    for i in range(start, end + 1):
                        tot += pos['zoom'][i]
                        nb += 1
                        med_list.append(pos['zoom'][i])
                        tot_per_zoom[pos['zoom'][i] - 1] += 1
                        nb_per_image[pos['zoom'][i] - 1] += 1
                    for i in range(config.MAX_ZOOM):
                        med_per_zoom[i].append(nb_per_image[i])
                        avg_per_zoom[i] += nb_per_image[i]
                else:
                    for i in range(config.MAX_ZOOM):
                        med_per_zoom[i].append(0)
            if nb == 0:
                ret.append(0)
            else:
                ret.append(float(tot)/nb)

            med_list.sort()
            if len(med_list) == 0:
                ret2.append(0)
            else:
                ret2.append(int(len(med_list)/2))

            for i in range(config.MAX_ZOOM):
                ret3[i].append(tot_per_zoom[i])
                if len(self.images) == 0:
                    ret4[i].append(0)
                else:
                    ret4[i].append(float(avg_per_zoom[i])/len(self.images))
                med_per_zoom[i].sort()
                if len(med_per_zoom[i]) == 0:
                    ret5[i].append(0)
                else:
                    ret5[i].append(med_per_zoom[i][int(len(med_per_zoom[i])/2)])

        # avg, median, tot_per, avg_per, med_per
        return ret, ret2, ret3, ret4, ret5

    def annotation_actions(self):
        """
        calculates annotation action variables for each user
        :return: 1) total
                 2) average
                 3) median
        """
        ret = []
        ret2 = []
        ret3 = []

        for user in self.user_list:
            tot = 0
            med = []
            for image_id in self.images:
                if image_id in self.images[image_id].user_actions:
                    action = self.images[image_id].user_actions[user.user_id]
                    start, end = self.start_end_indexes(action)
                    tot += end - start + 1
                    med.append(end - start + 1)
                else:
                    med.append(0)

            med.sort()
            ret.append(tot)
            if len(self.images) == 0:
                ret2.append(0)
            else:
                ret2.append(float(tot) / len(self.images))
            if len(med) == 0:
                ret3.append(0)
            else:
                ret3.append(med[int(len(med)/2)])

        return ret, ret2, ret3


    def user_scores(self):
        """
        calculates user score variables for each user
        :return: 1) average
                 2) per image scores (for each image a list of user scores )
                 3) per annotation scores (for each annotation a list of user scores)
                 4) the list of image ids respective to 2)
                 5) tha list of annotation ids respective to 3)
        """
        ret = []
        ret2 = [[] for image_id in self.images]
        ret3 = []
        ret4 = [image_id for image_id in self.images]
        ret5 = []
        for image_id in self.images:
            nb = self.images[image_id].nb_ref_annotations()
            for i in range(nb):
                ret3.append([])
                ret5.append((image_id, self.images[image_id].ref_annotations['id'][i]))

        for user in self.user_list:
            u = user.user_id
            tot = 0
            i = 0
            j = 0
            for image_id in self.images:
                nb = self.images[image_id].nb_ref_annotations()
                image = self.images[image_id]
                if u in image.user_positions and u in image.user_actions:
                    start_p, end_p = self.start_end_indexes(image.user_positions[u])
                    start_a, end_a = self.start_end_indexes(image.user_positions[u])
                    s, a = score_user_on_image(image.user_positions[u], image.user_actions[u], image,
                                               start_pos=start_p, start_action=start_a, end_pos=end_p, end_action=end_a)
                elif u in image.user_positions and u not in image.user_actions:
                    start_p, end_p = self.start_end_indexes(image.user_positions[u])
                    s, a = score_user_on_image(image.user_positions[u], None, image, start_pos=start_p, end_pos=end_p)
                else:
                    s = 0
                    a = None
                tot += s
                ret2[i].append(s)
                for k in range(nb):
                    if a is None:
                        ret3[j].append(0)
                    else:
                        ret3[j].append(a[k])
                    j += 1
                i += 1

            if len(self.images) == 0:
                ret.append(0)
            else:
                ret.append(float(tot)/len(self.images))

        return ret, ret2, ret3, ret4, ret5


    def per_image_nb_positions(self):
        """
        calculates per image number of positions variables for each user
        :return: 1) for each image a list of nb of positions
                 2) image ids
        """
        ret = []
        id = []
        for image_id in self.images:
            im_pos = []
            id.append(image_id)
            for user in self.user_list:
                if image_id in user.positions:
                    pos = user.positions[image_id]
                    start, end = self.start_end_indexes(pos)
                    im_pos.append(end - start + 1)
                else:
                    im_pos.append(0)
            ret.append(im_pos)
        return ret, id

    def per_image_time_spent(self):
        """
        calculates per image time spent variables for each user
        :return: 1) for each image a list of time spent values
                 2) image ids
        """
        ret = []
        id = []
        for image_id in self.images:
            im_time = []
            id.append(image_id)
            for user in self.user_list:
                if image_id in user.positions:
                    time = self.time_spent(image_id, user)
                    im_time.append(time)
                else:
                    im_time.append(0)
            ret.append(im_time)
        return ret, id

    def per_image_ann_actions(self):
        """
        calculates per image number of annotation action variables for each user
        :return: 1) for each image a list of annotation actions
                 2) image ids
        """
        ret = []
        id = []
        for image_id in self.images:
            im_act = []
            im = self.images[image_id]
            id.append(image_id)
            for user in self.user_list:
                u_id = user.user_id
                if u_id in im.user_actions:
                    act = im.user_actions[u_id]
                    start, end = self.start_end_indexes(act)
                    im_act.append(end - start + 1)
                else:
                    im_act.append(0)
            ret.append(im_act)
        return ret, id

    def per_image_zooms(self):
        """
        calculates per image number of positions variables for each zoom for each user
        :return: 1) for each image zoom pair a list of number of positions
                 2) image ids, zoom pairs
        """
        ret = []
        id = []
        for image_id in self.images:
            max_z = self.images[image_id].zoom_max
            im_pos = [[] for i in range(max_z)]
            for i in range(max_z):
                id.append((image_id, i + 1))

            for user in self.user_list:
                zooms = [0 for i in range(max_z)]
                if image_id in user.positions:
                    pos = user.positions[image_id]
                    start, end = self.start_end_indexes(pos)
                    if end > 0:
                        for i in range(start, end + 1):
                            zoom_id = pos['zoom'][i]
                            zooms[int(zoom_id) - 1] += 1
                for i in range(max_z):
                    im_pos[i].append(zooms[i])

            ret += im_pos
        return ret, id


    def ratio_during_module(self):
        """
        For the images in this module, the percentage of time worked during its time frame for each user
        :return: list
        """
        ret = []

        for user in self.user_list:
            tot = 0
            nb = 0
            for im_id in user.positions:
                pos = user.positions[im_id]
                tot += len(pos['timestamp'])
                start, end = self.start_end_indexes(pos)
                nb += end - start + 1

            if tot == 0:
                ret.append(0)
            else:
                ret.append(float(nb)/tot)

        return ret
