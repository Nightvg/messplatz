import serial
import numpy as np
from websocket import WebSocket, create_connection

import logging
from copy import deepcopy
import json
from threading import Timer, Lock
import pickle
from socket import socket, AF_INET, SOCK_DGRAM
from datetime import datetime

class ByteArray(bytes):
    def __init__(self, byte=b'') -> None:
        self = bytes(byte)
    def __call__(self, byte=b''):
        if isinstance(self, ByteArray):
            self = bytes(byte)
            return self
        return ByteArray(byte)
    def listMask(self, cmpList:list) -> list:
        tmp = self
        res = []
        for i in cmpList:
            res += [tmp[:i]]
            tmp = tmp[i:]
        return res

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

class Reader(serial.Serial):
    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the serial reader.

        Arguments:
            port        : serialport to retrieve data from
            baudrate    : datatransferrate in signes per second, usually bits
            ip          : ipv4 address of packer server
            sockport    : portnumber of packer server
            dps         : dataframes per second
            device      : devicename
            datatype    : list of types of inputdata, has to be the same type thoughout
                          the set of inputs
        """
        if 'dev' in kwargs and kwargs['dev']:
            super().__init__()
        else:
            self.__init(*args, **kwargs)
    
    def __init(self, port="COM3", baudrate=500000, ip="127.0.0.1", sockport=3001, dps=60, device='microcontroller', datatype:dict={'EMG1':np.float32, 'EMG2':np.float32, 'ECG':np.float32, 'BR':np.float32, 'EDA':np.float32}):
        super().__init__(port=port, baudrate=baudrate)
        self.Timer = RepeatTimer(1/dps, self.__run)
        self.__addr = (ip, sockport)
        self.datatype = datatype
        #see microcontroller for baudrate, port could change on differnt devices
        self.MAX_ATTEMPS = 5
        self.__ATTEMPTS = 0
        #number of bytes to read
        self.BUFFBYTES = sum([np.dtype(x).itemsize for x in self.datatype.values()])
        #constant value for incorrect read
        self.WRONGREAD = [np.frombuffer(bb*b'\x00', dt) for bb,dt in zip(self.BUFFBYTES, self.datatype.values())]
        #enlarge input buffer
        self.set_buffer_size(rx_size=8192, tx_size=1024) 
        #initialize readbuffer as byte type due to byte reading from pyserial
        self.reset_input_buffer()
        sock = socket(AF_INET, SOCK_DGRAM)
        self.datatype['Device'] = device
        sock.sendto(pickle.dumps(self.datatype), self.__addr)

    def __run(self):
        try:
            readout = [ByteArray(dFrame).listmask(self.BUFFBYTES) for dFrame in self.read_all().split(b'\r\n')]
            if len(readout) > 1:
                readbuff = readbuff[readbuff.rindex(b'\r\n')+2:] 
                self.sock.sendto(pickle.dumps(readout), self.__addr)
        except FileNotFoundError:
            if self.__ATTEMPTS > 5:
                return
            self.__ATTEMPTS += 1
            print('[SER-READER] Serial connection lost, trying to reconnect')
            self.open()    
        except Exception:
            pass   

    def start(self):
        self.Timer.start()
    def cancel(self):
        self.Timer.cancel()

class Packet_Manager():
    def __init__(self, ws_address: str, ws_port: int, reader_port: int, dps: int) -> None:
        threadbuff = {}
        lock = Lock
        addr = {}
        websocket = create_connection("ws://"+ws_address+":"+str(ws_port))
        reader_socket = socket(AF_INET, SOCK_DGRAM)
        reader_socket.bind(('',reader_port))
        self.__recvTimer = RepeatTimer(1/dps, Packet_Manager.__run_receiver(reader_socket))
        print('[PACKER] UDP socket ready')
        
    @staticmethod
    def run_receiver(reader_socket: socket, addr: dict, lock: Lock, threadbuff: dict):
        try:
            data, address = reader_socket.recvfrom(16384)
            if not address in addr.keys():
                lock.acquire()
                tmp = pickle.loads(data)
                tmp_device = tmp.pop('Device')
                addr[address] = tmp_device
                threadbuff[tmp_device] = {'Data':np.zeros((len(tmp),)), 'Keys':list(tmp.keys()), 'Known':False}
                lock.release()
                print('[PACKER] Registered ' + tmp_device)
            else:
                lock.acquire()
                tmp_data = pickle.loads(data)
                threadbuff[addr[address]]['Data'] = np.vstack((threadbuff[addr[address]]['Data'],tmp_data)).astype(tmp_data.dtype)
                lock.release()
        except Exception as e:
            print('[PACKER][ERROR] ' + str(e))

    @staticmethod
    def run_sender(lock: Lock, threadbuff: dict, websocket: WebSocket):
        lock.acquire()
        tmp_buff = deepcopy(threadbuff)
        for key in threadbuff.keys():
            if threadbuff[key]['Data'].ndim > 1:
                threadbuff[key]['Data'] = threadbuff[key]['Data'][-1]
        lock.release()
        for device, dict_data in tmp_buff.items():
            res = {'data':None,'device':device}
            if not dict_data['Known']:
                res['names'] = dict_data['Keys']
                lock.acquire()
                threadbuff[device]['Known'] = True
                lock.release()
            if dict_data['Data'].ndim > 1:
                res['data'] = np.mean(dict_data['Data'][:-1], axis=0).tolist()
                #self.__websocket.send(json.dumps({'data':data[-1].tolist(), 'device': device}))
                #print(data[:-1])
            else:
                res['data'] = dict_data['Data'].tolist()
            websocket.send(json.dumps(res))
