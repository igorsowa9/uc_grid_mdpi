import json
import requests
import sys
import time
import numpy as np
from datetime import datetime
import multiprocessing
from controller_config import *
import paho.mqtt.client as paho
import itertools
import pandas as pd
from csv import writer
from send import *
from send import *
from receive import receive
pd.set_option("display.max_rows", None, "display.max_columns", None)

device_type_rtds = "rtds1"
device_type_pmu = "pmu"
device_id_rtds = "rtds001"

pmu_signals = ["v10_m","v10_a","v10_f","v10_r","v10_t"]

# MGCC with:
# PDC function for synchronization between real pmu and rtds measurements (also phasors there)
# power sharing: centralized for grid forming and two grid feeding: in order to minimize the infeed of grid forming
# improvement of this behaviour through direct feeding of PMU measurements to grid feeding.

ran = np.concatenate((rtds_names, rtds_text)).tolist()
ras = np.concatenate((rtds_signals, rtds_tsignals)).tolist()

pan = [0]*(len(channel_names)*len(sub_names))
pas = [0]*(len(channel_names)*len(sub_names))
for ai in range(len(channel_names)):
    a = channel_names[ai]
    a1 = channel_signals[ai]
    for bi in range(len(sub_names)):
        b = sub_names[bi]
        b1 = sub_signals[bi]
        pan[ai * len(sub_names) + bi] = str(a) + str(b)
        pas[ai * len(sub_names) + bi] = str(a1) + "_" + str(b1)

# structures with measurement values to share using Manager between the processes
meas_set_rtds = multiprocessing.Manager().list(np.zeros(len(ras)).tolist())  # measurements from RTDS to update
meas_set_pmu = multiprocessing.Manager().list(np.zeros(len(pas)).tolist())
meas_synch = multiprocessing.Manager().list(np.zeros(len(ras)+len(pas)+1).tolist())  # measurements from RTDS to update

# Setpoints updated by different modules (or one) and sent to devices (VM). See config for what is what
setpoints = multiprocessing.Manager().list(default_controls)


def get_setpoints_fromRTDS():
    global meas_set_rtds, meas_set_pmu
    time.sleep(1)
    while True:
        ldata = receive(IP_receive, Port_receive, NumData_fromRTDS)
        npdata = np.round(np.array(receive(IP_receive, Port_receive, NumData_fromRTDS)), 8)

        ts_prec = 3 # down to miliseconds only
        ts_m = np.round(datetime.now().timestamp(), ts_prec)
        ts_ms = np.round(np.round(datetime.now().timestamp(), ts_prec) * 10**ts_prec)
        other_data = np.array([ts_ms, pd.Timestamp(ts_m, unit='s')])
        meas_set_rtds[0:18] = ldata[0:18]
        meas_set_rtds[18] = ts_ms
    return


def get_setpoints_fromDB():
        # Request to orion:
    #url = "134.130.166.184:1026/v2/entities/Simulation:RTDS:1/attrs/i1f?type=rtds1&options=keyValues"
    #
    # /v2/entities/?type=pmu,rtds1&attrs=v10_a,v10_r,il2an columns = ""
    global meas_set_rtds, meas_set_pmu
    columns = ""
    for col in rtds_signals:
        columns = columns + col + ","
    url1 = 'http://' + cloud_ip + ":1026/v2/entities/Simulation:RTDS:1?attrs="+columns
    h = {'Accept': 'application/json',
        'fiware-service': fiware_service,
        'fiware-servicepath': fiware_servicepath}

    columns = ""
    for col in pmu_signals:
        columns = columns + col + ","
    url2 = 'http://' + cloud_ip + ":1026/v2/entities/Simulation:PMU:1?attrs=" + columns

    print("starting queries to DB")
    while True:
        print("\n\nGet from DB--------------------")
        response = requests.get(url1, headers=h)
        parsed = json.loads(response.text)
        count = 0
        for col in rtds_signals:
            meas_set_rtds[count] = parsed[col]['value']
            count = count + 1
        print(meas_set_rtds)

        response = requests.get(url2, headers=h)
        parsed = json.loads(response.text)
        count = 0
        for col in pmu_signals:
            meas_set_pmu[count] = parsed[col]['value']
            count = count + 1
        print(meas_set_pmu)
        #time.sleep(Tc)
    return

    # through sql request to crate
    url = 'http://' + cloud_ip + ':4200/_sql'
    h = {'Content-Type': 'application/json',
        'fiware-service': fiware_service,
        'fiware-servicepath': '/'}
    columns = ""
    for col in rtds_signals:
        columns = columns + col + ", "
    d = {"stmt":"SELECT " + columns[:-2] +" FROM mt" + fiware_service + ".et" + device_type_rtds + " ORDER BY time_index DESC limit 1"}
    d = json.dumps(d).encode('utf8')
    response = requests.post(url, data=d, headers=h)
    parsed = json.loads(response.text)
    #meas_set = np.array(parsed['rows'])
    print("RTDS: " + str(parsed))

    d = {"stmt":"SELECT * FROM mt" + fiware_service + ".et"+device_type_pmu+" ORDER BY time_index DESC limit 1"}
    d = json.dumps(d).encode('utf8')
    response = requests.post(url, data=d, headers=h)
    parsed = json.loads(response.text)
    #meas_set = np.array(parsed['rows'])
    print("PMU: " + str(parsed))

    return


def mqtt_loop1():
    """ Subscribes to the devices directly instead of obtaining data from DB."""
    client_rtds = paho.Client("cli1")
    client_rtds.on_connect = on_connect_rtds
    client_rtds.on_message = on_message_rtds
    client_rtds.connect(cloud_ip)
    print('mqtt loop1: starting. Subscribed to: ' + str(rtds_topic))
    client_rtds.loop_forever()


def mqtt_loop2():
    client_pmu = paho.Client("cli2")
    client_pmu.on_connect = on_connect_pmu
    client_pmu.on_message = on_message_pmu
    client_pmu.connect(cloud_ip)
    print('mqtt loop2: starting. Subscribed to: ' + str(pmu_topic))
    client_pmu.loop_forever()


def on_connect_rtds(client, userdata, flags, rc):
    print("Connected (RTDS) with result code "+str(rc))
    client.subscribe(rtds_topic)


def on_connect_pmu(client, userdata, flags, rc):
    print("Connected (PMU) with result code "+str(rc))
    client.subscribe(pmu_topic)


def append_list_as_row(file_name, list_of_elem):
    with open(file_name, 'a+', newline='') as file:
        csv_writer = writer(file)
        csv_writer.writerow(list_of_elem)


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return "Value error in find_between"


def on_message_rtds(client, userdata, msg):
    global meas_set_rtds
    #print("Topic: " + msg.topic+" Payload: "+str(msg.payload))
    entire_str = msg.payload.decode("utf-8")
    for ri in range(len(ran)):
        if not ri == len(ran)-1:
            val = find_between(str(entire_str+"|end"), ran[ri]+"|", "|"+ran[ri+1])
        else:
            val = find_between(str(entire_str + "|end"), ran[ri] + "|", "|end")
        try:
            meas_set_rtds[ras.index(ras[ri])] = np.round(float(val), 3)
        except ValueError:
            print("on_message_rtds error!")
            meas_set_rtds[ras.index(ras[ri])] = 0
    print(meas_set_rtds)
    return
    # delay at measurement arrival, if necessary
    ts_measurement = meas_set_rtds[ras.index("ts_measurement")]
    delay = datetime.utcnow().timestamp() * 1000 - float(ts_measurement)  # TIMESTAMP measured --------------

    print("New RTDS measurement: delay " + str(np.round(delay / 1000, 3)) +
          "s (measurement (" + str(ts_measurement) + ") to PDC of controller). Current rtds measurements buffer: " + str(df_rtds))
    return


def on_message_pmu(client, userdata, msg):
    global ns_pmu
    entire_str = msg.payload.decode("utf-8")
    #print("topic: " + str(msg.topic) + "\t payload:" + str(entire_str))
    for ri in range(len(pan)):
        if not ri == len(pan)-1:
            val = find_between(str(entire_str+"|end"), pan[ri] + "|", "|" + pan[ri+1])
        else:
            val = find_between(str(entire_str + "|end"), pan[ri] + "|", "|end")
        try:
            meas_set_pmu[pas.index(pas[ri])] = np.round(float(val), 3)
        except ValueError:
            meas_set_pmu[pas.index(pas[ri])] = 0
    return
    # delay at measurement arrival, if necessary
    ts_measurement = meas_set_pmu[pas.index("vo1a_timestamp")]
    delay = datetime.utcnow().timestamp() * 1000 - float(ts_measurement)
    print("New PMU measurement: delay " + str(np.round(delay / 1000, 3)) +
          "s (measurement (" + str(ts_measurement) + ") to PDC of controller). Current pmu measurements buffer: " + str(df_pmu))
    return


def pdc_mqtt():
    """ for now only taking the most recent, not synchronizing anything"""

    time.sleep(2)
    while 1==1:
        #time.sleep(Tc)
        meas_synch[0] = round(datetime.utcnow().timestamp() * 1000, 0)
        meas_set_pmu2 = [float(ele) for ele in meas_set_pmu]
        if np.isnan(meas_set_rtds).any() or np.isnan(meas_set_pmu2).any():
            print("Ignored NaN measurements!")
            continue
        meas_synch[1:6] = meas_set_pmu2
        meas_synch[6:] = meas_set_rtds
        #print(meas_synch)


def controller():
    integral_p2 = 0
    integral_p3 = 0
    integral_q2 = 0
    integral_q3 = 0
    print("starting controller")
    time.sleep(1)

    while True:
        #time.sleep(Tc*2)
        # check flags
        print(meas_synch)
        p_reset = meas_synch[12]
        q_reset = meas_synch[13]
        if p_reset == 0:
            print("\tp reset")
            integral_p2 = 0
            integral_p3 = 0
        if q_reset == 0:
            print("\tq reset")
            integral_q2 = 0
            integral_q3 = 0

        # assign/calculate measurements

        # load 2 ( with real pmu signal or with RTDS only)
        v10ma_pmu = meas_synch[1] # pmu
        v10ma = meas_synch[20] # rtds
        il2ma = meas_synch[22]
        theta_il2 = meas_synch[23]
        theta_v10_pmu = meas_synch[2] # pmu
        theta_v10 = meas_synch[21] # rtds
        pl2pmu = 3*v10ma*il2ma*np.cos(theta_v10-theta_il2)
        ql2pmu = 3*v10ma*il2ma*np.sin(theta_v10-theta_il2)

        # load 1
        v9ma = meas_synch[16]
        il1ma = meas_synch[18]
        theta_il1 = meas_synch[19]
        theta_v9 = meas_synch[17]
        pl1pmu = 3*v9ma*il1ma*np.cos(theta_v9-theta_il1)
        ql1pmu = 3*v9ma*il1ma*np.sin(theta_v9-theta_il1)

        po1 = meas_synch[6] # grid forming
        qo1 = meas_synch[7]
        po2 = meas_synch[8] # grid feeding 1
        qo2 = meas_synch[9]
        po3 = meas_synch[10] # grid feeding 2
        qo3 = meas_synch[11]

        print("theta_v10 (rtds)=" + str(theta_v10))
        print("theta_v10 (pmu)=" + str(theta_v10_pmu))
        print("v10ma=" + str(v10ma))
        print("theta_v10=" + str(theta_v10))
        print("il2ma=" + str(il2ma))
        print("theta_il2=" + str(theta_il2))

        print("pl2pmu=" + str(pl2pmu))
        print("ql2pmu=" + str(ql2pmu))
        print("pl1pmu=" + str(pl1pmu))
        print("ql1pmu=" + str(ql1pmu))
        print("po1=" + str(po1))
        print("qo1=" + str(qo1))
        print("po2=" + str(po2))
        print("qo2=" + str(qo2))
        print("po3=" + str(po3))
        print("qo3=" + str(qo3))

        #continue

        # refs/params
        dt = 0.01 # seconds
        p1ref = 0
        q1ref = 0
        sec_coeff1 = 1
        sec_coeff2 = 1
        pmu_coeff1 = 0.6

        # errors
        dp2 = ((po3 - po2) * sec_coeff1 + po1) * sec_coeff2
        dq2 = ((qo3 - qo2) * sec_coeff1 + qo1) * sec_coeff2
        dp3 = dp2
        dq3 = dq2

        print("dp2/3 =" + str(dp2))
        print("dq2/3 =" + str(dq2))

        # integration
        ki_p2 = 0.20
        ki_p3 = 0.20
        ki_q2 = 0.20
        ki_q3 = 0.20

        integral_p2 = integral_p2 + ki_p2 * dt * dp2
        integral_p3 = integral_p3 + ki_p3 * dt * dp3
        integral_q2 = integral_q2 + ki_q2 * dt * dq2
        integral_q3 = integral_q3 + ki_q3 * dt * dq3

        # output of power sharing control
        p2_sec = integral_p2
        p3_sec = integral_p3
        q2_sec = integral_q2
        q3_sec = integral_q3

        p2pmu_sec = pmu_coeff1 * (pl1pmu+pl2pmu)
        p3pmu_sec = p2pmu_sec
        q2pmu_sec = pmu_coeff1 * (ql1pmu+ql2pmu)
        q3pmu_sec = q2pmu_sec

        setpoints[0:8] = [p2_sec, q2_sec, p3_sec, q3_sec, p2pmu_sec, q2pmu_sec, p3pmu_sec, q3pmu_sec]
        setpoints[8] = meas_synch[0]
        setpoints[9] = 0 # ts_patch added just before sending

        # send setpoints either as patch request or as direct socket message to RTDS
        if patch_or_socket == 1:
            url = 'http://' + cloud_ip + ':1026/v2/entities/Simulation:RTDS:1/attrs?type=' + device_type_rtds
            h = {'Content-Type': 'application/json', 'fiware-service': fiware_service, 'fiware-servicepath': fiware_servicepath}
            d = {}
            for rc in range(len(rtds_commands)):
                val = setpoints[rc]
                d.update({rtds_commands[rc]: {
                    "type": "command",
                    "value": str(val)
                }})

            ts_patch = datetime.utcnow().timestamp() * 1000
            d['ts_patch']['value'] = str(ts_patch)
            d = json.dumps(d).encode('utf8')
            response = requests.patch(url, d, headers=h)
            print("setpoint sent!: " + str(setpoints))
            print(response.status_code, response.reason, " -- ", response.text)
            delay_rtds_pdc = meas_synch[0] - meas_synch[24]
            print("delay_rtds_pdc: " + str(delay_rtds_pdc) + " ms")

            if True:
                print(response.status_code, response.reason)  # HTTP
                print(response.text)  # TEXT/HTML

            if str(response.status_code) == "204":
                print("\t\tSend_setp.: Successful patch request with setpoints: " + str(setpoints) )

            # send also to the visualisation database
            if False:
                controller_payload = "p1|" + str(setpoints[P1]) + "|p2|" + str(setpoints[P2]) + "|ts|" + str(setpoints[TS_PDC]) + "|dc|0.0" # + str(setpoints[DESC])

                print("Payload before publishing: \n" + str(controller_payload))
                client2 = paho.Client("cloud")
                client2.on_publish = on_publish_visualisation  # assign function to callback
                client2.connect(broker_ip, port)
                client2.publish("/" + api_key + "/" + device_id_rtds + "/attrs/", controller_payload)

        elif patch_or_socket == 0:
            print('Sending to RTDS: starting')
            ts_execute = round(datetime.utcnow().timestamp() * 1000, 0)
            send(setpoints[0:8], IP_send, Port_send)  # substitute last with 0 due to ts
            print("\tSent values at ts_execute (direct)	="+str(ts_execute)+" : " + str(setpoints[0:8]) + " Based on ts_pdc = " + str(setpoints[8]))
            delay_pdc_exec = ts_execute - setpoints[8]
            delay_rtds_pdc = meas_synch[0] - meas_synch[24]
            print("delay_rtds_pdc: " + str(delay_rtds_pdc) + " ms")
            print("delay_pdc_exec: " + str(delay_pdc_exec) + " ms")

        # save timestamps to csv
        print("saving to CSV in controller")
        ts_pmu = meas_synch[0]
        ts_rtds = meas_synch[24]
        ts_pdc = setpoints[8]
        append_list_as_row("/home/iso/MDPI_with_Sebastian/controller_results.csv", [ts_pmu, ts_rtds, ts_pdc, ts_patch])

def main():
    """ Runs parallel processes of the controller (secondary control):
    (i) data download from DB/ from devices,
    (ii) continous PQ control for f and V control,
    (iii) descrete actions of controller, e.g. load shedding for frequency control"""

#    get_setpoints_fromDB()
 #   return
    p0 = multiprocessing.Process(target=get_setpoints_fromDB)
    #p0 = multiprocessing.Process(target=get_setpoints_fromRTDS)
    p0.start()

    #p1 = multiprocessing.Process(target=mqtt_loop1)  # subscribe directly from MQTT Broker instead of from DB
    #p2 = multiprocessing.Process(target=mqtt_loop2)
    #p1.start()
    #p2.start()

    p3 = multiprocessing.Process(target=pdc_mqtt)
    p3.start()

    p4 = multiprocessing.Process(target=controller)
    p4.start()
    # p5 = multiprocessing.Process(target=sc_continous)
    # p5.start()
    # p6 = multiprocessing.Process(target=send_setpoints)
    # p6.start()

    p0.join()
    #p1.join()
    #p2.join()
    p3.join()
    p4.join()
    # p5.join()
    # p6.join()
    return


if __name__ == "__main__":
    main()
    #get_setpoints_fromDB()


## [16:37] Sebastian Blechmann
## 134.130.166.184:8668/v2/entities/Simulation:PMU:1?type=PMU [16:37] Sebastian Blechmann
##  DELETE + headers
