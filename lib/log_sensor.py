#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: log_and_count.py 

author: jom52
license : GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

log errors and manage counters
v0.1.0 : 27.01.2022 --> first prototype
v0.1.1 : 31.01.2022 --> get_and_log_error_info added logic for simple str messages
v0.1.2 : 01.02.2022 --> added automatic management of the counters (if necessary creaate file and new counter)
v0.1.3 : 02.02.2022 --> corection on the function couters
v0.1.4 : 02.02.2022 --> correction on the function log error
v0.1.5 : 05.02.2022 --> modified log and count to log the count of the same error
v0.1.6 : 08.02.2022 --> correction of error introduced in v0.1.5
v0.1.7 : 08.02.2022 --> no more file error.txt. All counter in are now in the file counter.txt
v0.1.8 : 23.02.2022 --> addd file name and line number on error
v0.1.9 : 22.06.2022 --> log_error modified for 'more_info'
v0.1.10 : 27.06.2022 --> log_error modified presnetations of recorded data
v0.1.11 : 27.06.2022 --> log_error modified for display cpl correctly
-----------------------------------------------------------------------------------------
v0.2.0 : 07.09.2022 --> log_error modified for display line error number ---> no more compatible with previous versions
-----------------------------------------------------------------------------------------
v0.3.0 : 12.03.2023 --> ajout de la date et heure de la survenance d'une erreur
v0.3.1 : 15.03.2023 --> amélioration des procédures log_error et error_detail
v3.3.2 : 07.06.2023 --> correction in log_error gor OSError
V3.3.3 : 19.04.2024 --> pris la date et l'heure sur la RTC
v3.3.4 : 20.03.2024	--> log_error, ajouté l'option "record_time" yes-no
v3.3.5 : 21.04.2024 --> ajouté un compteur de messages d'erreur pour éviter l'enregistrement de trop de lignes pour un seul problème
"""
from sys import print_exception 
from io import StringIO
counter_file_name = 'counter.txt'
error_file_name = 'errors.txt'

class LogSensors:
    
    def __init__(self):
        self.msg_header = ' -<>- '

    def counters(self, counter_name, add1=False):
        increment = 1 if add1 else 0
        try: # test if the file exist, if yes read the data's
            with open (counter_file_name, 'r') as f:
                lines = f.readlines()
                # the file exist check if the counter exist    
                c_exist = False
                for line in lines:
                    try:
                        c_name, _ = line.split(':')
                        if c_name.strip() == counter_name.strip():
                            c_exist = True
                    except:
                        pass
        except: # file do not exist --> create and initialise the counter
            with open(counter_file_name, 'w') as f:
                f.write(counter_name + ':' + str(increment) + '\n')
                return increment
              
        if c_exist:
            # the counter exist
            if add1:
                # incease and record new value
                with open (counter_file_name, 'w') as f:
                    for line in lines:
                        try:
                            c_name, c_val = line.split(':')
                            c_val = int(c_val)
                            if c_name.strip() == counter_name.strip():
                                c_val += increment
                                v_ret = c_val
                            f.write(c_name + ':' + str(c_val) + '\n')
                        except:
                            pass
                    return v_ret
            else:
                # just return the value
                for line in lines:
                    c_name, c_val = line.split(':')
                    c_val = int(c_val)
                    if c_name == counter_name:
                        return c_val
        else:
            # the counter dont exist so create it and initialise to increment value
            with open(counter_file_name, 'a') as f:
                f.write(counter_name + ':' + str(increment) + '\n')
                return increment

    def supress_msg_head(self, txt, search_str):
        pos_find = txt.find(search_str)
        if pos_find != -1:
            return ((txt[pos_find + len(search_str):]).strip())
        else:
            return txt
            
    def log_error(self, info, err_info='', to_print = False):
        
        # create info message
        if err_info is not None:
            try:
                err_info = err_info.replace(':','')
            except:
                pass
        head = '1 time' + self.msg_header
        error_msg = str(info + ', ' + err_info if err_info else info)
        
        try: # check existing file, if yes open and read the data's
            with open (error_file_name, 'r') as f:
                file_text = f.readlines()
        except: # file not exist --> create and initialise the counter to increment value
            with open(error_file_name, 'w') as f:
                f.write(head + error_msg + '\n')
            if to_print: print(head + error_msg)
            self.counters('error', True)
            # the file is created so the job is finished
            return
        
        # the file exists but it's empty
        if len(file_text) == 0 :
            with open(error_file_name, 'w') as f:
                f.write(head + error_msg + '\n')
            if to_print: print(head + error_msg)
            self.counters('error', True)
            return
        
        # file exists and there is already records
        # records are in file_text
        with open (error_file_name, 'w') as f:
            found = False
            for line in file_text:
#                 line.replace('\n', '')
                # search for a number in the line just before the first space
                try:
                    val = int(line[:line.find(' ')]) + 1 # increment the number
                except:
                    val = 1
                # verify if the message already exist in the curent line
                msg_short = self.supress_msg_head(error_msg, self.msg_header)
                line_short = self.supress_msg_head(line, self.msg_header)
                if msg_short == line_short: # the error message was found in the curent line
                    line = str(val) + ' times' + self.msg_header + msg_short + '\n'
                    found = True
                    if to_print: print(line.replace('\n', ''))
                    self.counters('error', True)
                f.write(line)
            # the message has not been found so add a new line
        if not found:
            with open (error_file_name, 'a') as f:
                line = '1 time' + self.msg_header + msg_short + '\n'
                f.write(line)
                if to_print: print(line.replace('\n', ''))
                self.counters('error', True)

    def error_detail(self, err_info):
        s = StringIO()
        print_exception(err_info, s)  
        s = s.getvalue()
        s = s.split('\n')                                                                   
        err = s[1].strip() + ", " + s[2].strip().replace(':', ',')
        return err

def main():
    logsensors = LogSensors()
    import math
    
    i = 0
    while i < 1:
        i += 1
        try:
#             f = open("xxx.txt")
            a=1/0
#             a = math.log(-1)
            pass
        except Exception as err:
            logsensors.log_error(info = 'LogSensor test',
                                  err_info = logsensors.error_detail(err),
                                  to_print = True)
        
    print('test counters', logsensors.counters('test counters', True))

if __name__ == '__main__':
    main()
