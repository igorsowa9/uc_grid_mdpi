import socket
import sys
import os
import struct
from datetime import datetime, timedelta
import paho.mqtt.client as paho
import multiprocessing
import numpy as np
from random import random
import time
from send import send
from controller_config import *
from csv import writer
from tofloat import tofloat

manager = multiprocessing.Manager()

# Default values
data_received = manager.list(default_controls)  # with min_ts to pass

# #############################################
# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# server_address = (IP_receive, Port_receive)
# sock.bind(server_address)
#
# NumData = 1
# num_data_rcv = NumData
# num_data_rcv = int(num_data_rcv)
#
# print('\nWaiting to receive message')
# data, address = sock.recvfrom(4096)
# print(data)
#
# ldata = [round(tofloat(data[(4*x):(4+4*x)]), 6) for x in range(0, NumData)]
# print('Type of ldata: ', type(ldata))
# print('ldata=', ldata)
#
# # send([0.1, 0.3, 0.1], '134.130.169.96', 12334)
# server_address = ('134.130.169.96', 12334)
#
# # print(struct.pack('!f', 1.0))
# a = struct.pack('!f', 1.1)
# print(a)
# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sent = sock.sendto(a, server_address)
# print(sent)
#
# exit(0)
#
# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# NumElements = len(data)
# print(NumElements)
#
# # create the array
# a = struct.pack('>f', data[0])
# for i in range(1, NumElements):
#     a += struct.pack('>f', data[i])
#     print(struct.pack('>f', data[i]))
#
# print(a)
# sent = sock.sendto("", server_address)
# exit(0)
#
# ##############################################

# file for results accessible from controller:
with open('results_vm2rtds.csv', 'w', newline='') as file:
    csv_writer = writer(file)
    csv_writer.writerow(["ts_pdc", "ts_execute"])


def append_list_as_row(file_name, list_of_elem):
    with open(file_name, 'a+', newline='') as file:
        csv_writer = writer(file)
        csv_writer.writerow(list_of_elem)


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("/asd1234rtds/rtds001/cmd")  # Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print("Topic: " + msg.topic+" Payload: " + str(msg.payload))
    entire_str = msg.payload.decode("utf-8")

    if "rtds001@p2_setpoint|" in entire_str:
        value = float(entire_str.replace("rtds001@p2_setpoint|", ""))
        data_received[0] = value
    elif "rtds001@q2_setpoint|" in entire_str:
        value = float(entire_str.replace("rtds001@q2_setpoint|", ""))
        data_received[1] = value
    elif "rtds001@p3_setpoint|" in entire_str:
        data_received[2] = float(entire_str.replace("rtds001@p3_setpoint|", ""))
    elif "rtds001@q3_setpoint|" in entire_str:
        data_received[3] = float(entire_str.replace("rtds001@q3_setpoint|", ""))
    elif "rtds001@p2pmu_setpoint|" in entire_str:
        data_received[4] = float(entire_str.replace("rtds001@p2pmu_setpoint|", ""))
    elif "rtds001@q2pmu_setpoint|" in entire_str:
        data_received[5] = float(entire_str.replace("rtds001@q2pmu_setpoint|", ""))
    elif "rtds001@p3pmu_setpoint|" in entire_str:
        data_received[6] = float(entire_str.replace("rtds001@p3pmu_setpoint|", ""))
    elif "rtds001@q3pmu_setpoint|" in entire_str:
        data_received[7] = float(entire_str.replace("rtds001@q3pmu_setpoint|", ""))
    elif "rtds001@ts_pdc|" in entire_str:
        data_received[8] = float(entire_str.replace("rtds001@ts_pdc|", ""))
    elif "rtds001@ts_patch|" in entire_str:
        data_received[9] = float(entire_str.replace("rtds001@ts_patch|", ""))
    else:
        print("another setpoint than expected")


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def mqtt_loop():
    client = paho.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(cloud_ip, 1883, 60)
    print('mqtt loop: starting')
    client.loop_forever()


def send_to_RTDS():
    print('Sending to RTDS: starting')
    mem_ts_pdc = 0
    while True:
        curr_data_received = data_received
        data_to_RTDS = curr_data_received[0:-2]
        if mem_ts_pdc == curr_data_received[-2]:
            continue
        print("TS_PDC in received data (no-reps): " + str(curr_data_received[-2]))
        print("TS_Patch in received data (no-reps): " + str(curr_data_received[-1]))
        ts_execute = round(datetime.utcnow().timestamp() * 1000, 0)
        send(data_to_RTDS, IP_send, Port_send)  # substitute last with 0 due to ts
        print("\tSent values at ts="+str(ts_execute)+" : " + str(data_to_RTDS) +
              " with delay to ts_pdc (not min_ts!): " + str(ts_execute-float(mem_ts_pdc)) + "ms")

        #append_list_as_row("results_vm2rtds.csv", [mem_ts_pdc, ts_execute])
        #mem_ts_pdc = curr_data_received[-2]

        # time.sleep(0.01)


if __name__ == '__main__':
    p1 = multiprocessing.Process(target=mqtt_loop)
    p1.start()
    p2 = multiprocessing.Process(target=send_to_RTDS)
    p2.start()
    p1.join()
    p2.join()
