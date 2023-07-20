#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file: airsens_graph_details.py  

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens_v3

data management for the project airsens esp32-mqtt-mysql

v0.1.0 : 17.07.2023 --> first prototype
"""
import sys
import socket
import mysql.connector
import matplotlib.pyplot as plt
# import pandas as pd
# import numpy as np
# import pyautogui
import math

VERSION_NO = '0.1.0'
PROGRAM_NAME = 'airsens_graph_details.py'


class AirSensBatGraph:

    def __init__(self):
        # database
        self.database_username = "pi"  # YOUR MYSQL USERNAME, USUALLY ROOT
        self.database_password = "mablonde"  # YOUR MYSQL PASSWORD
        self.host_name = "localhost"
        self.server_ip = '10.0.0.120'
        self.database_name = 'airsens'
        # graph
#         self.filter = 30
#         self.filter_day = int(24 * 60 / 5) # moyene sur mesure = 24h * 60m / 5m (intervalle)
        self.reduce_y2_scale_factor = 2.5
    
    def convert_sec_to_hms(self, seconds):
        min, sec = divmod(seconds, 60)
        hour, min = divmod(min, 60)
#         return "%d:%02d" % (hour, min)
#         return str(hour) +"h " + str(min) + "m"
        return '{:0d}'.format(int(hour))  + "h " + '{:0d}'.format(int(min)) + "m"

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
        elapsed_s = ((date_end[0][0] - date_start[0][0]).total_seconds())
        elaps_hm = self.convert_sec_to_hms(elapsed_s)
        
        d = elapsed_s // (24 * 3600)
        elapsed_s = elapsed_s % (24 * 3600)
        h = elapsed_s // 3600
        elapsed_s %= 3600
        m = elapsed_s // 60
        elapsed_s %= 60
        str_elapsed = '{:02d}'.format(int(d)) + '-' + '{:02d}'.format(int(h)) + ':' + '{:02d}'.format(int(m))
        str_elapsed = '{:02d}'.format(int(d)) + 'j ' + '{:2d}'.format(int(h)) + 'h ' + '{:2d}'.format(int(m)) + 'm'
        return str_elapsed, elaps_hm


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

    def get_quantity(self, sensor_type, sensor_location):

        sql_txt = " ".join([
            "SELECT DISTINCT quantity.quantity",
            "FROM quantity",
            "INNER JOIN airsens ON quantity.id = airsens.quantity",
            "WHERE",
            "airsens.sensor_location = '" + str(sensor_location) + "'",
            "AND airsens.sensor_type = '" + str(sensor_type) + "'",
            "OR airsens.sensor_type = '3'",
            "ORDER BY quantity.id;"])
        print(sql_txt)

        db_connection, err = self.get_db_connection(self.database_name)
        db_cursor = db_connection.cursor()
        db_cursor.execute(sql_txt)
        data = db_cursor.fetchall()
        for d in data:
            print(d[0])
        return data


    def get_id(self, table, field, val):

        db_connection, err = self.get_db_connection(self.database_name)
        db_cursor = db_connection.cursor()
        sql_txt_1 = "SELECT id FROM " + table + " WHERE " + field + "='" + val + "';"
#         print(sql_txt_1)
        db_cursor.execute(sql_txt_1)
        s_id = db_cursor.fetchall()
        try:
            return s_id[0][0]
        except:
            return None

    def is_prime(self, n): # retourne True si n est un nombre premier
        for i in range(2,int(math.sqrt(n))+1):
            if (n%i) == 0:
                return False
        return True

    def get_hv(self, locaux):
        
        # return the number of graph in hor(n_h) and in vert(n_v) and a tuple with the list of positions for pyplot(plot:place) 
        nbre_locaux = len(locaux) # number of graphs to draw
        if nbre_locaux < 3:
            n_v = 2
            n_h = 1
            plot_place = (0,1,)
            return n_v, n_h, plot_place
        else:
            # if number of graph is a prime number increment it
            if self.is_prime(nbre_locaux): nbre_locaux += 1
            # get the square root of graph_nubmer
            sqr_nbre_locaux = math.sqrt(nbre_locaux)
            # get all the divisors for the graph_numer
            divisors = [i for i in range(2, nbre_locaux) if nbre_locaux % i == 0]
            # get the gap between divisors and square roor
            ecarts = {j : abs(d - sqr_nbre_locaux) for j, d in enumerate(divisors)} 
            # search the index of the smallest gap
            ecarts_values = list( ecarts.values())
            ecarts_keys = list( ecarts.keys())
            min_value = min( ecarts_values)
            divisor_index_min = ecarts_keys[ecarts_values.index(min_value)]
            # the divisor of the smalest gap is the hor number of graphs
            n_h = divisors[divisor_index_min]
            # calculate the vert number of graphs and if nbre vert is not and integer incrmente it
            n_v = int(nbre_locaux / n_h)
            if nbre_locaux / n_h != int(nbre_locaux / n_h): n_v += 1
            # get the presentation table for the graphs
            plot_place = () 
            plot_place += tuple((h,v) for h in range(n_h) for v in range(n_v))
        
        return n_v, n_h, plot_place

    def plot_air_data(self, sensor_name, s_location, s_id, s_type, sensor_spec):
        
        color = ['blue', 'red', 'brown', 'green', 'black']
        font = {'family': 'serif', 'color': 'darkred', 'weight': 'normal', 'size': 16, }
        
        sensor_type = str(self.get_id('sensor_type', 'sensor_type', s_type))
        sensor_location = str(self.get_id('sensor_location', 'sensor_location', s_location))
#         print('sensor_type:', s_type, 'sensor_location:', s_location)
        
        quantities = self.get_quantity(sensor_type, sensor_location)
        n_v, n_h, plot_place = self.get_hv(quantities)
        fig, ax1 = plt.subplots(n_h, n_v)
#         print('n_v, n_h, plot_place:', n_v, n_h, plot_place)
        
        for i, q_y in enumerate(quantities):
#             print(q_y[0])
            
            q_id = str(self.get_id('quantity', 'quantity', str(q_y[0])))
            print(q_id)
            if str(q_y[0]) == 'bat':
                s_type = '3'
            else:
                s_type=sensor_type
            sql_txt = " ".join([
                "SELECT time_stamp, value",
                "FROM airsens",
                "INNER JOIN quantity ON airsens.quantity = quantity.id",
                "INNER JOIN sensor_type ON airsens.sensor_type = sensor_type.id",
                "INNER JOIN sensor_location ON airsens.sensor_location = sensor_location.id",
                "WHERE sensor_location.id = '" + sensor_location + "'",
                    "AND sensor_type.id = '" + s_type + "'", 
                    "AND quantity.id = '" + q_id + "'",
                "ORDER BY airsens.id;"])
            print(sql_txt)

            db_connection, err = self.get_db_connection(self.database_name)
            db_cursor = db_connection.cursor()
            db_cursor.execute(sql_txt)
            data = db_cursor.fetchall()
            if data:
                x_data = [x[0] for x in data]
                y_data = [y[1] for y in data]

                ax1[plot_place[i]].plot(x_data, y_data, color=color[i])
                ax1[plot_place[i]].tick_params(labelrotation=0)
                ax1[plot_place[i]].set_ylabel(q_y)
                ax1[plot_place[i]].grid(True)
                ax1[plot_place[i]].plot(x_data, y_data, color=color[i])
                ax1[plot_place[i]].set_title(q_y)
                
            fig.legend('aaaaaa', loc='upper center')
        plt.show()  # plot

    def main(self):
        print('runing airsen_v3_details V' + VERSION_NO)
        """
        locaux{} is a dictionary with the structure:
        'key':[location, id, sensor_type, spec]
        """
        locaux = {
            'mtl_1':     ['mtl_1', 'D6:b4', 'bme280', '+5V-30s'],
            'mtl_2':     ['mtl_2', 'E8:D4', 'bme280', 'bat-30s'],
            'solar_bme': ['solar', 'F3:24', 'bme280', 'bat-30s'],
#             'solar_hdc': ['F3:24', 'solar', 'hdc1080', 'bat-30s'],
            }
        print('nbre_locaux:',len(locaux))
        for local in locaux.items():
            print()
            print('working for:', str(local[0]) + ' - ' + str(local[1]))
            self.plot_air_data(local[0], local[1][0], local[1][1], local[1][2], local[1][3])
        print('end')

if __name__ == '__main__':
    # instantiate the class
    airsens_bat_graph = AirSensBatGraph()
    # run main
    airsens_bat_graph.main()
