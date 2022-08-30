import serial
import pickle
import numpy as np
from time import sleep
import socket

def reader_init(port="COM3", baudrate=500000, ip="127.0.0.1", sockport=3001, dps=30) -> None:
    """
    Initialize and starts the serial reader as \'run forever\'. Needs to be started befor packer and node server.
    Arguments:
        port        : serialport to retrieve data from                      | str
        baudrate    : datatransferrate in signes per second, usually bits   | int
        ip          : ipv4 address of packer server                         | str
        sockport    : portnumber of packer server                           | int
        dps         : dataframes per second                                 | int
    Returns:
        None
    """ 
    #see microcontroller for baudrate, port could change on differnt devices
    conn = serial.Serial(port=port, baudrate=baudrate, timeout=0.01) 
    wrongread = np.frombuffer(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', np.float32)
    #enlarge input buffer
    conn.set_buffer_size(rx_size=8192, tx_size=1024) 
    #initialize readbuffer as byte type due to byte reading from pyserial
    readbuff = b'' 
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conn.flushInput()
    dps = 1/dps
    while conn.is_open:
        try:
            readbuff += conn.read_all()
            tmp = readbuff.split(b'\r\n')[:-1]
            readout = np.array([np.frombuffer(x, np.float32) if len(x)==20 else wrongread for x in tmp])       
            if len(readout) > 1:
                readbuff = readbuff[readbuff.rindex(b'\r\n')+2:] 
                sock.sendto(pickle.dumps(readout), (ip, sockport))
        except:
            pass
        finally:
            sleep(dps) #30 dataframes per second as default

#reader_init()