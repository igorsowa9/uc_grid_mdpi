import numpy as np
#import pandapower as pp

# fiware_service = "grid_uc"
fiware_service = "pmu"
fiware_servicepath = "/test01" # <- test01 for Sebastian's tests

# subscription of data from RTDS and PMU (directly, not through CrateDB)
rtds_topic = "/ul/asd1234rtds/rtds001/attrs"
pmu_topic = "/ul/asd1234/pmu001/attrs"

#cloud_ip = "134.130.166.184" # <- Sebastian's setup
cloud_ip = "127.0.0.1"
#api_key = "asd1234controller"
broker_ip = cloud_ip
port = 1883
iotport = '4062'
#iotport = '4061' # 4061 for Sebastian's setup, 4062 standard

IP_send = '134.130.169.99'  # of GTNET, not rack, not own IP - it works like a subnet therefore IP of the GTnet + 0.0.0.3
IP_receive = '134.130.169.12'  # should be updated by the current public (depending on configuration) IP address
Port_send = 12334
Port_receive = 12334
patch_or_socket = 1

# RTDS
NumData_fromRTDS = 18
rtds_names = np.array(["rtds1", "rtds2", "rtds3", "rtds4", "rtds5", "rtds6", "rtds7", "rtds8", "rtds9", "rtds10", "rtds11", "rtds12", "rtds13", "rtds14", "rtds15", "rtds16", "rtds17", "rtds18"])
rtds_text = np.array(["ts_rtds"])
rtds_signals = np.array(["p1", "q1", "p2", "q2", "p3", "q3", "synch_form_P", "synch_form_Q", "i1d_lim_sw", "vPPS", "il1", "dil1", "vl1", "dvl1", "il2", "dil2", "vl2", "dvl2"])
rtds_tsignals = np.array(["ts"])

default_controls = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
rtds_commands = np.array(["p2_setpoint", "q2_setpoint", "p3_setpoint", "q3_setpoint", "p2pmu_setpoint", "q2pmu_setpoint", "p3pmu_setpoint", "q3pmu_setpoint", "ts_pdc", "ts_patch"])
rtds_commands_names = np.array(["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"])

pps_signal_idx = 9 # index of vPPS in the message from RTDS

# PMU
channel_names = np.array(["ch0"])
sub_names = np.array(["a", "b", "c", "d", "e"])

channel_signals = np.array(["v10"])
sub_signals = np.array(["m", "a", "f", "r", "t"])

# controller
ki_P = 0.1
ki_Q = 0.1

# PDC
Fc = 100
Tc = 0.5/Fc # removed for now!
mem_size = 1  # sizes of df_rtds/pmu processed in PDC

sequence_ms = 400  #  1000  # that often the whole sequence of synchronization run, what define a granularity of calculations
delay_ms = 200  # 200  # that much delay can each sequence allow. After they are either approximated or copied.
pdc_init_sleep = 0.3
pdc_loop_sleep = 0.7  # 0.05s/20 Hz minus some for processing (?) -> 0.039

data_fromDB = False  # data from controller either from DB (True) or directly through MQTT subscription from meters

