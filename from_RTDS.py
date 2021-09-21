import numpy as np
import paho.mqtt.client as paho
import time
from datetime import datetime
import pandas as pd
import random

# import own RPI2 scripts
from receive import receive
from controller_config import *

#fiware_service = "grid_test2" <- in settings
device_type = "rtds1"
device_id = "rtds001"

broker_ip = "127.0.0.1"  # if tunelled! 10.12.0.10
# broker_ip = "134.130.166.184"
for_controller = broker_ip
# for_controller = "137.226.248.118"

port = 1883
api_key = "asd1234rtds"

f_reporting = 100
dt = 1e6/f_reporting
ts = 0
pps_signal_previous = 0
dt_fixing = -2
vpps_counter = 0
sec_counter = 0

def on_publish(client, userdata, result):
    print("RTDS data published to cloud! \n")
    pass


def storedata_attempt(client1, client2):
    global ts
    global pps_signal_previous, vpps_counter, sec_counter

    # receive from RTDS:
    ldata = receive(IP_receive, Port_receive, NumData_fromRTDS)
    npdata = np.round(np.array(receive(IP_receive, Port_receive, NumData_fromRTDS)), 8)

    # assigning timestamp just as local ts - it should come from RTDS too
    ts_prec = 3
    ts_m = np.round(datetime.now().timestamp(), ts_prec)
    ts_ms = np.round(np.round(datetime.now().timestamp(), ts_prec) * 10**ts_prec)
    other_data = np.array([ts_ms, pd.Timestamp(ts_m, unit='s')])
    #print("Values received from RTDS: ", npdata)

    # build message
    payload = ""
    payload_print  = ""
    for r in np.arange(len(rtds_names)):
        rn = rtds_names[r]
        value = npdata[r]
        payload += rn + "|" + str(value) + "|"

    pps_signal = npdata[pps_signal_idx]
    if vpps_counter == 0 and pps_signal == 0:
        print("No PPS yet. Continue.")
        return
    if (pps_signal > 0.5 and pps_signal_previous < 0.5):
        ts = 1e6+dt_fixing*dt
        vpps_counter = vpps_counter + 1
    else:
        ts = (ts + dt) % 1e6

    if ts == 0.0:
       sec_counter = sec_counter + 1
    absolute_ts = (sec_counter*1e6 + ts)/1e6

    payload += "ts_rtds|"+str(int(ts))
    pps_signal_previous = pps_signal

    topic = "/ul/asd1234rtds/rtds001/attrs"
    client2.publish(topic, payload) # publishing through Orion


def storedata_once(client1, client2):
    storedata_attempt(client1, client2)
    while True:
        try:
            storedata_attempt(client1, client2)
        except:
            print("Unexpected error:", sys.exc_info())
            # logging.error(" When: " + str(datetime.now()) + " --- " + "Error in storedataOnce(): ", sys.exc_info())
        else:
            break


def storedata_repeatedly():
    client1 = paho.Client("controller")  # create client object
    client2 = paho.Client("cloud")
    client2.on_publish = on_publish  # assign function to callback

    client1.connect(for_controller, port)  # establish connection
    client2.connect(broker_ip, port)
    while True:
        storedata_once(client1, client2)

storedata_repeatedly()
