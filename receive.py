import socket
from tofloat import tofloat


def receive(IP, Port, NumData):

	# Create a UDP socket
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	# Bind the socket to the port
	server_address = (IP, Port)
	# print('starting up on {} port {}'.format(*server_address))
	sock.bind(server_address)

	num_data_rcv = NumData
	num_data_rcv = int(num_data_rcv)

	# print('\nWaiting to receive message')
	data, address = sock.recvfrom(4096)
	# print('received {} bytes from {}'.format(len(data), address))
	# print('Original type of data: ', type(data)); print('Original data: ', data)
	# print('...received from RTDS!')

	ldata = [round(tofloat(data[(4*x):(4+4*x)]),6) for x in range(0, NumData)]
	#print('Type of ldata: ', type(ldata))

	return ldata


