#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file: airsens_graph_compare.py  

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

data management for the project airsens esp32-mqtt-mysql

v0.1.0 : 18.02.2022 --> first prototype
v0.1.1 : 19.02.2022 --> added filtered voltage and delta % of the voltage
v0.1.2 : 19.02.2022 --> changed the calculation of d_bar scale (d_m)
v0.1.3 : 21.02.2022 --> grid for bat uniform for the 2 axes
v0.1.4 : 23.02.2022	--> adjusted the size of the graph the the whole screen
v0.1.5 : 02.06.2022 --> added local p2
v0.1.6 : 06.06.2022 --> addeb battery life on graph
v0.1.7 : 12.09.2022 --> use dictonary for graph list
v0.2.0 : 16.09.2022 --> added day mean for temp, hum, pres
v0.2.1 : 18.09.2022 --> cosmetical changes
"""
import sys
import socket
import mysql.connector
import matplotlib; matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np

VERSION_NO = '1.0.0'
PROGRAM_NAME = 'airsens_graph_compare.py'


def convert_sec_to_hms(seconds):
    minutes, sec = divmod(seconds, 60)
    hour, minutes = divmod(minutes, 60)
    return '{:0d}'.format(int(hour)) + "h " + '{:0d}'.format(int(minutes)) + "m"


class AirSensTempGraph:

    def __init__(self):
        # database
        self.database_username = "pi"  # YOUR MYSQL USERNAME, USUALLY ROOT
        self.database_password = "mablonde"  # YOUR MYSQL PASSWORD
        self.host_name = "localhost"
        self.server_ip = '10.0.0.120'
        self.database_name = 'airsens'

    def get_db_connection(self, db):
        # get the local IP adress
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        # verify if the mysql server is ok and the db avaliable
        try:
            if local_ip == self.server_ip:  # if we are on the RPI with mysql server (RPI making temp acquis)
                # test the local database connection
                con = mysql.connector.connect(user=self.database_username, password=self.database_password,
                                              host=self.host_name, database=db)
            else:
                # test the distant database connection
                con = mysql.connector.connect(user=self.database_username, password=self.database_password,
                                              host=self.server_ip, database=db)
            return con, sys.exc_info()
        except:
            return False, sys.exc_info()

    def get_data(self, sensor_type, sensor_location, quantity):

        sql_txt = "".join([
            # "SELECT time_stamp, sensor_id.sensor_id, \
            #     sensor_location.sensor_location, sensor_type.sensor_type, quantity.quantity, value",
            "SELECT time_stamp, value",
            " FROM airsens",
            " INNER JOIN quantity ON airsens.quantity = quantity.id",
            " INNER JOIN sensor_type ON airsens.sensor_type = sensor_type.id",
            " INNER JOIN sensor_location ON airsens.sensor_location = sensor_location.id",
            # " INNER JOIN sensor_id ON airsens.sensor_id = sensor_id.id",
            " WHERE sensor_location.sensor_location = '" + sensor_location + "' \
                AND sensor_type.sensor_type = '" + sensor_type + "' \
                AND quantity.quantity = '" + quantity + "'",
            " ORDER BY airsens.id;"])
#         print(sql_txt)

        db_connection, err = self.get_db_connection(self.database_name)
        db_cursor = db_connection.cursor()
        db_cursor.execute(sql_txt)
        data = db_cursor.fetchall()
        x_data = [x[0] for x in data]
        temp_data = [y[1] for y in data]

        return x_data, temp_data

    def get_elapsed_time(self, local):

        db_connection, err = self.get_db_connection(self.database_name)
        db_cursor = db_connection.cursor()
        # get the start time and date
        sql_duree_debut = 'SELECT time_stamp FROM airsens WHERE local="' + local + '" ORDER BY id ASC LIMIT 1;'
        db_cursor.execute(sql_duree_debut)
        date_start = db_cursor.fetchall()
        # get the end time and ddate
        sql_duree_fin = 'SELECT time_stamp FROM airsens WHERE local="' + local + '" ORDER BY id DESC LIMIT 1;'
        db_cursor.execute(sql_duree_fin)
        date_end = db_cursor.fetchall()
        # close the db
        db_cursor.close()
        db_connection.close()
        # calculate the battery life time
        elapsed_s = int((date_end[0][0] - date_start[0][0]).total_seconds())
        elaps_hm = convert_sec_to_hms(elapsed_s)
        elaps_s = elapsed_s

        d = elapsed_s // (24 * 3600)
        elapsed_s = elapsed_s % (24 * 3600)
        h = elapsed_s // 3600
        elapsed_s %= 3600
        m = elapsed_s // 60
        elapsed_s %= 60
        str_elapsed = '{:02d}'.format(int(d)) + 'j ' + '{:2d}'.format(int(h)) + 'h ' + '{:2d}'.format(int(m)) + 'm'
        return str_elapsed, elaps_hm, elaps_s

    def plot_compare(self, locaux):
#         print('locaux:', locaux)

        # plot_filtered_data = False
        fig, ax1 = plt.subplots(3,1)
        # adjust the size of the graph to the screen
        fig.set_figheight(5.5)
        fig.set_figwidth(10)

        color = ['blue', 'red', 'brown', 'green', 'black']
        font = {'family': 'serif', 'color': 'darkred', 'weight': 'normal', 'size': 16, }

        for i, local_d in enumerate(locaux.items()):
#             print('local_d:', local_d)

            local = local_d[1][3]
            print('working for:', str(local_d[0]) + ' - ' + str(local_d[1]))
            # bat
            # get data from db
            time_x, bat = self.get_data('bat', local, 'bat')
            print('nbre data:', len(time_x))
            if len(time_x):
                # battery
                ax1[0].tick_params(labelrotation=0)
                ax1[0].set_ylabel('[V]')
                ax1[0].grid(True)
                ax1[0].plot(time_x, bat, color=color[i])#, label=local + ': ' + local_d[1][0])

            # hum
            # get data from db
            time_x, hum = self.get_data(str(local_d[1][1]), local, 'hum')
            print('nbre data:', len(time_x))
            if len(time_x):
            # humidity
                ax1[1].tick_params(labelrotation=0)
                ax1[1].set_ylabel('[%]')
                ax1[1].grid(True)
                ax1[1].plot(time_x, hum, color=color[i])#, label=local + ': ' + local_d[1][0])
            # temp
            # get data from db
            time_x, temp = self.get_data(str(local_d[1][1]), local, 'temp')
            print('nbre data:', len(time_x))
            if len(time_x):
            # temperature
                ax1[2].tick_params(labelrotation=0)
                ax1[2].set_ylabel('[°C]')
                ax1[2].grid(True)
                ax1[2].plot(time_x, temp, color=color[i], label = local + ': ' + local_d[1][0] + ' ' + local_d[1][1])

        fig.legend(loc='center right')
        fig.suptitle(PROGRAM_NAME + ' ' + VERSION_NO)
        plt.subplots_adjust(left=0.1,
                            bottom=0.1,
                            right=0.9,
                            top=0.9,
                            wspace=0.2,
                            hspace=0.4)
        plt.xticks(rotation=0)
        ax1[2].set_yticks(np.linspace(ax1[2].get_yticks()[0], ax1[2].get_yticks()[-1], len(ax1[2].get_yticks())))
#         plt.savefig('temp.pdf', orientation='Landscape')
        plt.show()  # plot

    def main(self):
        print('runing airsen_graph V' + VERSION_NO)
        locaux = {
            'mtl_2': ['E8:D4', 'bme280', 'bat-30s', 'mtl_2'],
            'solar': ['F3:24', 'bme280', 'bat-30s', 'solar'],
#             'solar_11': ['F3:24', 'hdc1080', 'bat-30s', 'solar'],
            'mtl_1': ['D6:b4', 'bme280', '+5V-30s', 'mtl_1'],
        }
#         print(locaux)
        print('nbre_locaux:', len(locaux))
        self.plot_compare(locaux)


if __name__ == '__main__':
    # instantiate the class
    airsens_temp_graph = AirSensTempGraph()
    # run main
    airsens_temp_graph.main()
