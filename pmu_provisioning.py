import json
import requests
import time
import paho.mqtt.client as paho
import numpy as np
import sys
from controller_config import *

n_pmu_analog_channels = 8  # determined by number of chanells in DAQ
n_pmu_streams_to_cloud = 40  # 8x5 from each channel with have magn, ang, freq, rocof, time, ... (?)

# channel_names = np.array(["ch0", "ch1", "ch2", "ch3", "ch4", "ch5"])
# sub_names = np.array(["a", "b", "c", "d", "e"])
#
# channel_signals = np.array(["vo1a", "vo2a", "vo3a", "vo4a", "v3a", "vt"])
# sub_signals = np.array(["magnitude", "frequency", "angle", "rocof", "timestamp"])

device_type = "pmu" # <- table's name
device_id = "pmu001"

api_key = "asd1234"


def on_publish(client,userdata,result):             #create function for callback
    print("My data published! \n")
    pass


## provisioning communication: device(mqtt)-though MQTT Broker and Orion- to Quantum Leap + Crate DB + Grafana
print("\n Provisioning communication:"
      "\n\t\t - PMU measurements to FIWARE")

# 1. pushing the model
print("\n --> 1. Provisioning PMU data model.")

url = 'http://' + cloud_ip + ':1026/v2/entities'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': fiware_servicepath}

d = {
        "id": "Simulation:PMU:1",
        "type": device_type}

for ch in np.arange(len(channel_names)):
    ch_n = channel_names[ch]
    ch_s = channel_signals[ch]

    for k in sub_signals:
        key = str(ch_s) + "_" + str(k)
        value = {"value": 0.0}
        d2 = {key: value}
        d.update(d2)

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason, " -- ", response.text)  # HTTP # TEXT/HTML
time.sleep(1)

# 2. provisioning a service group for mqtt
print("\n --> 2. Provisioning a service group for mqtt")

url = 'http://' + cloud_ip + ':' + iotport + '/iot/services'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': fiware_servicepath}
d = {
    "services": [
       {
           "apikey": api_key,
           "cbroker": "http://orion:1026",
           "entity_type": device_type,
           "resource": "/iot/d"
       }
    ]
}

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason, " -- ", response.text)  # HTTP # TEXT/HTML
time.sleep(1)

# 3. provisioning sensors
print("\n --> 3. Provisioning sensors")

url = 'http://' + cloud_ip + ':'+iotport+'/iot/devices'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': fiware_servicepath}

attributes = []

for ch in np.arange(len(channel_names)):
    ch_n = channel_names[ch]
    ch_s = channel_signals[ch]

    for sub in np.arange(len(sub_names)):
        sn = sub_names[sub]
        ss = sub_signals[sub]

        value1 = ch_n + sn
        value2 = ch_s + "_" + ss
        di = {"object_id": value1, "name": value2, "type": "Number"}
        if sn == "e":
            di = {"object_id": value1, "name": value2, "type": "Text"}
        attributes.append(di)

d = {
"devices": [
   {
     "device_id":   "" + device_id + "",
     "entity_name": "Simulation:PMU:1",
     "entity_type": "" + device_type + "",
     "protocol":    "PDI-IoTA-UltraLight",
     "transport":   "MQTT",
     "timezone":    "Europe/Berlin",
     "attributes": attributes
   }
]
}

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason, " -- ", response.text)  # HTTP # TEXT/HTML
time.sleep(1)

# 4. making subscriptions of QL
print("\n --> 4. Making subscriptions of QL")

url = 'http://' + cloud_ip + ':1026/v2/subscriptions/'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': fiware_servicepath}

attrs = []

for ch in np.arange(len(channel_names)):
    ch_s = channel_signals[ch]
    for sub in np.arange(len(sub_names)):
        ss = sub_signals[sub]
        value2 = ch_s + "_" + ss
        attrs.append(value2)

d = {
       "description": "Notification Quantumleap",
       "subject": {
           "entities": [
               {"id": "Simulation:PMU:1", "type": device_type}
           ],
           "condition": {
               "attrs": attrs
           }
               },
           "notification": {
                "http": {"url": "http://quantumleap:8668/v2/notify"},
                "attrs": attrs,
            "metadata": ["dateCreated", "dateModifid"]
           },
       "throttling": 0
}

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason, " -- ", response.text)  # HTTP # TEXT/HTML

client1 = paho.Client("control1")  # create client object
client1.on_publish = on_publish  # assign function to callback
client1.connect(broker_ip, port)  # establish connection

test_payload = ""
for ch in np.arange(len(channel_names)):
    ch_n = channel_names[ch]
    for sub in np.arange(len(sub_names)):
        sn = sub_names[sub]
        test_payload += ch_n + sn + "|" + "0.0"
        if not (ch == len(channel_names)-1 and sub == len(sub_names)-1):
            test_payload += "|"

print("\nTest command (not executed):\n")
print("mosquitto_pub -h "+broker_ip+" -t \"/ul/"+api_key+"/"+device_id+"/attrs\" -m \""+test_payload+"\" ")

# ret = client1.publish("/" + api_key + "/" + device_id + "/attrs", test_payload)
