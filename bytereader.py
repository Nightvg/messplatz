import serial
import struct
import numpy as np
from datetime import datetime
from time import sleep
import json
import socket

def xtof(arg) -> list:
    return [float(struct.unpack('f',arg[start:stop])[0]) for start,stop in zip([0,4,8,12,16],[4,8,12,16,20])] if len(arg) == 20 else [0,0,0,0,0]

file = open('test.txt','w')
conn = serial.Serial(port='COM3', baudrate=500000, timeout=0.01)
conn.set_buffer_size(rx_size=8192, tx_size=1024)
readbuff = b''
sock = websockets.connect('ws://127.0.0.1:8080')
s = datetime.now()
e = s
bytesize = 0
linesize = 0
conn.flushInput()
while conn.is_open and (e-s).total_seconds() < 5:
    readbuff += conn.read_all()
    bytesize += len(readbuff)
    readout = np.array([xtof(x) for x in readbuff.split(b'\r\n')[:-1]])
    linesize += readout.shape[0]
    writeout = '\n'.join([','.join(x) for x in readout.astype(str)]) + '\n'
    sock.send(json.dumps(np.mean(readout, axis=1)))
    
    if len(writeout) > 1:
        file.write(writeout)
        readbuff = readbuff[readbuff.rindex(b'\r\n')+2:] 
    sleep(0.033)
    e = datetime.now()

file.close()
print('Bytes: ', bytesize)
print('Lines: ', linesize)
#print('Tmplist: ', len(tmplist))
print(e-s)