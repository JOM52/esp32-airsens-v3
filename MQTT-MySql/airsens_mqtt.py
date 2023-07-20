#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file: airsens_mqtt.py

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

data management for the project airsens esp32-mqtt-mysql

v0.1.0 : 05.07.2023 --> first prototype based on airsens_mqtt.py
v0.1.1 : 17.07.2023 --> error on s_type for bat corrected
"""
VERSION = '0.1.1'
APP = 'airsens_mqtt'

import paho.mqtt.client as mqtt
import time
import sys
import socket
import mysql.connector
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class AirSensNow:


    def __init__(self):
        # airsens
        self.msg_count = 0
        # battery
        self.UBAT_100 = 4.5
        self.UBAT_0 = 3.6
        # database
        self.database_username = "pi"  # YOUR MYSQL USERNAME, USUALLY ROOT
        self.database_password = "mablonde"  # YOUR MYSQL PASSWORD
        self.host_name = "localhost"
        self.server_ip = '10.0.0.120'
        self.database_name = 'airsens'
        # email
        self.sender_address = 'esp32jmb@gmail.com'
        self.sender_pass = 'wasjpwyjenoliobz'
        self.receiver_address = 'jmetra@outlook.com'
        self.mail_send = False
        # mqtt
        self.mqtt_ip = '10.0.0.120'
        self.client = None
        self.mqtt_topic = "airsens_v3"

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

    def send_email(self, title, msg):
        # Setup the MIME
        message = MIMEMultipart()
        message['From'] = self.sender_address
        message['To'] = self.receiver_address
        message['Subject'] = title
        # The body and the attachments for the mail
        message.attach(MIMEText(msg, 'plain'))
        # Create SMTP session for sending the mail
        session = smtplib.SMTP('smtp.gmail.com', 587)  # use gmail with port
        session.starttls()  # enable security
        session.login(self.sender_address, self.sender_pass)  # login with mail_id and password
        text = message.as_string()
        session.sendmail(self.sender_address, self.receiver_address, text)
        session.quit()
        print('Mail Sent')

    def get_id(self, field, val):

        db_connection, err = self.get_db_connection(self.database_name)
        db_cursor = db_connection.cursor()
        sql_txt_1 = "SELECT id FROM " + field + " WHERE " + field + "='" + val + "';"
        try:
            db_cursor.execute(sql_txt_1)
            s_id = db_cursor.fetchall()
            return s_id[0][0]
        except:
            print('erroooooor')
            return 0


    def get_set_id(self, field, val):

        db_connection, err = self.get_db_connection(self.database_name)
        db_cursor = db_connection.cursor()
        sql_txt_1 = "SELECT id FROM " + field + " WHERE " + field + "='" + val + "';"
        # print('sql_txt_1:', sql_txt_1)
        try:
            db_cursor.execute(sql_txt_1)
            s_id = db_cursor.fetchall()
        except:
            print('erroooooor')
            return 0
        if not s_id:
            sql_txt_2 = "INSERT INTO sensor_id(" + field + ") VALUES('" + val + "');"
            sql_txt_2 = "INSERT INTO " + field + "(" + field + ") VALUES('" + val + "');"
            # print('sql_txt_2:', sql_txt_2)

            db_cursor = db_connection.cursor()
            db_cursor.execute(sql_txt_2)
            db_connection.commit()

            db_cursor = db_connection.cursor()
            db_cursor.execute(sql_txt_1)
            s_id = db_cursor.fetchall()
        # print('sensor_id:', s_id)
        return s_id[0][0]

    def record_data_in_db(self, sensor_id, sensor_location, sensor_type, quantity, value):

        s_id = self.get_set_id("sensor_id", sensor_id)
        s_type = self.get_set_id("sensor_type", sensor_type)
        s_location = self.get_set_id("sensor_location", sensor_location)
        s_quantity = self.get_set_id("quantity", quantity)
        if s_quantity == 4:
            s_type = self.get_id("sensor_type", 'bat')
#         print('s_id:', s_id, 'stype:', s_type, 's_location:', s_location, 's_quantity:', s_quantity)

        if s_id and s_type and s_location:
            sql_txt = "".join(["INSERT INTO airsens (sensor_id, sensor_location, sensor_type, quantity, value ) VALUES "
                               "(", "'", str(s_id), "',",
                               "'", str(s_location), "',",
                               "'", str(s_type), "',",
                               "'", str(s_quantity), "',",
                               "'", str(value), "');"])
            # print(sql_txt)
            db_connection, err = self.get_db_connection(self.database_name)
            db_cursor = db_connection.cursor()
            db_cursor.execute(sql_txt)
            db_connection.commit()
        else:
            print('DB ERROR')


    def get_begin_end_and_elapsed_time(self, sensor_location):

        # get the start time and date
        db_connection, err = self.get_db_connection(self.database_name)
        db_cursor = db_connection.cursor()
        sql_duree_debut = 'SELECT time_stamp FROM airsens ' \
                          'WHERE sensor_location="' + sensor_location + '" ORDER BY id ASC LIMIT 1;'
        db_cursor.execute(sql_duree_debut)
        date_start = db_cursor.fetchall()
        # get the end time and ddate
        sql_duree_fin = 'SELECT time_stamp FROM airsens WHERE sensor_location="' + sensor_location + '" ORDER BY id DESC LIMIT 1;'
        db_cursor.execute(sql_duree_fin)
        date_end = db_cursor.fetchall()
        # close the db
        db_cursor.close()
        db_connection.close()
        # calculate the elapsed time
        str_now = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime())
        try:
            elapsed = ((date_end[0][0] - date_start[0][0]).total_seconds())
        except:
            elapsed = 0
        d = elapsed // (24 * 3600)
        elapsed = elapsed % (24 * 3600)
        h = elapsed // 3600
        elapsed %= 3600
        m = elapsed // 60
        elapsed %= 60
        str_elapsed = '{:02d}'.format(int(d)) + '-' + '{:02d}'.format(int(h)) + ':' + '{:02d}'.format(int(m))
        # return the calculate values
        return str(date_start), str(date_end), str_elapsed

    # This is the Subscriber
    def on_connect(self, client, userdata=None, flags=None, rc=None):
        print(APP + " V" + VERSION + " connected to mqtt topic " + client + " on " + self.mqtt_ip)
        print('--------------------------------------------------------------------------')
        self.client.subscribe(client)

    # This is the message manager
    def on_message(self, client, userdata, msg):
        # decode the message
        self.msg_count += 1
        rx_msg = msg.payload.decode()
        topic, sensor_id, sensor_location, sensor_type, data = rx_msg.split('/')
        dt_begin, dt_end, elapsed = \
            self.get_begin_end_and_elapsed_time(str(self.get_id('sensor_location', sensor_location)))
        print(self.msg_count, elapsed, sensor_id, sensor_location, sensor_type, end=' ')
        data_1 = data.split(',')
        for d1 in data.split(','):
            d1 = d1.replace('[', '').replace(']', '').replace("'", '')
            quantity = d1.split(':')[0].strip()
            value = float(d1.split(':')[1])
            print(quantity + ':' + str(value), end=' ')
            self.record_data_in_db(sensor_id, sensor_location, sensor_type, quantity, value)
        print('')

    def main(self):
        # connect on the mqtt client
        self.client = mqtt.Client()
        self.client.connect(self.mqtt_ip, 1883, 60)
        # mqtt interrup procedures
        self.client.on_connect = self.on_connect(self.mqtt_topic)
        self.client.on_message = self.on_message
        # loop for ever
        self.client.loop_forever()


if __name__ == '__main__':
    # instatiate the class
    airsens = AirSensNow()
    # run main
    airsens.main()
