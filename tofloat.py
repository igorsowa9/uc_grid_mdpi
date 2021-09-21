import struct

def tofloat(data):
	x = struct.unpack('>f',struct.pack('4B',*data))[0]
	return x
