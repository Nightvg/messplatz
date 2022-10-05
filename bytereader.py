#Standardlib
from pickle import dumps
from time import sleep
from socket import socket, AF_INET, SOCK_DGRAM
#Extern Packages
import numpy as np
import json
from serial import Serial

def reader_init(port="COM3", baudrate=500000, ip="127.0.0.1", sockport=3001, dps=60, device='microcontroller', datatype:dict={'EMG1':np.float32, 'EMG2':np.float32, 'ECG':np.float32, 'BR':np.float32, 'EDA':np.float32}):
    """
    Initialize and starts the serial reader as \'run forever\'. Needs to be started befor packer and node server.

    Arguments:
        port        : serialport to retrieve data from
        baudrate    : datatransferrate in signes per second, usually bits
        ip          : ipv4 address of packer server
        sockport    : portnumber of packer server
        dps         : dataframes per second
        device      : devicename
        datatype    : list of types of inputdata, has to be the same type thoughout
                      the set of inputs
    Returns:
        
    """
    #see microcontroller for baudrate, port could change on differnt devices
    conn = None
    attempts = 0
    while conn == None and attempts < 5:
        try:
            conn = Serial(port=port, baudrate=baudrate, timeout=0.01) 
        except:
            attempts += 1
            print('[SER-READER] Coud not open serial connection, attempt ',attempts)
            sleep(2)
    if attempts == 5:
        print('[SER-READER] Could not open serial connection, shuting down..')
        return
    else:
        attempts = 0
    #number of bytes to read
    BUFFBYTES = np.dtype(datatype['ECG']).itemsize*len(datatype)
    #constant value for incorrect read
    WRONGREAD = np.frombuffer(BUFFBYTES*b'\x00', datatype['ECG'])
    #enlarge input buffer
    conn.set_buffer_size(rx_size=8192, tx_size=1024) 
    #initialize readbuffer as byte type due to byte reading from pyserial
    readbuff = b'' 
    sock = socket(AF_INET, SOCK_DGRAM)
    datatype['Device'] = device
    sock.sendto(dumps(datatype), (ip, sockport))
    conn.flushInput()
    dps = 1/dps
    while True and attempts < 5:
        try:
            readbuff += conn.read_all()
            tmp = readbuff.split(b'\r\n')[:-1]
            readout = np.array([np.frombuffer(x, datatype['ECG']) if len(x)==BUFFBYTES else WRONGREAD for x in tmp])       
            if len(readout) > 1:
                readbuff = readbuff[readbuff.rindex(b'\r\n')+2:] 
                sock.sendto(dumps(readout), (ip, sockport))
        except FileNotFoundError:
            attempts += 1
            print('[SER-READER] Serial connection lost, trying to reconnect')
            conn.open()    
        except Exception:
            pass       
        finally:
            sleep(dps) #60 dataframes per second as default
    print('[SER-READER] Could not reconnect, shuting down')
#reader_init()