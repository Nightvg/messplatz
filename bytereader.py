import serial
import struct
import numpy as np
from datetime import datetime

datetime.now()

def xtof(arg) -> list:
    return [float(struct.unpack('f',arg[start:stop])[0]) for start,stop in zip([0,4,8,12,16],[4,8,12,16,20])] if len(arg) == 20 else [arg]

file = open('test.txt','w')
conn = serial.Serial(port='COM3', baudrate=500000, timeout=0.01)
conn.set_buffer_size(rx_size=8192, tx_size=1024)
readbuff = b''
s = datetime.now()
e = s
i = 0
bytesize = 0
linesize = 0
conn.flushInput()
while conn.is_open and (e-s).total_seconds() < 1:
    readbuff += conn.read_all()
    bytesize += len(readbuff)
    readout = np.array([xtof(x) for x in readbuff.split(b'\r\n')[:-1]]) if i > 0 else np.array([xtof(x) for x in readbuff.split(b'\r\n')[1:-1]])
    linesize += readout.shape[0]
    writeout = '\n'.join([','.join(x) for x in readout.astype(str)]) + '\n'
    if len(writeout) > 1:
        file.write(writeout)
        readbuff = readbuff[readbuff.rindex(b'\r\n'):] 
    e = datetime.now()

file.close()
print('Bytes: ', bytesize)
print('Lines: ', linesize)
#print('Tmplist: ', len(tmplist))
print(e-s)