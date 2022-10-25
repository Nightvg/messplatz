import serial
import numpy as np
from websocket import WebSocket, create_connection

import logging
import asyncio
from copy import deepcopy
import json
from threading import Thread, Timer, Lock
import pickle
from socket import socket, AF_INET, SOCK_DGRAM
from datetime import datetime, timedelta

class ByteArray(bytes):
    def __new__(cls, byte=b''):
        return super().__new__(cls, byte)
    def listMask(self, cmpList:list) -> list:
        return self.__recList(self, cmpList)
    @staticmethod
    def __recList(lList, stop) -> list:
        if len(lList) == 0:
            return []
        if len(stop) == 0:
            return [lList]
        return [lList[:stop[0]]] + ByteArray.__recList(lList[stop[0]:],stop[1:])
        
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
    
    def __init(self, port="COM3", baudrate=500000, ip="127.0.0.1", sockport=3001, time_port=2020, dps=60, device='microcontroller', datatype:dict={'EMG1':np.float32, 'EMG2':np.float32, 'ECG':np.float32, 'BR':np.float32, 'EDA':np.float32}):
        super().__init__(port=port, baudrate=baudrate)
        self.__timer = RepeatTimer(1/dps, self.__run)
        self.__addr = (ip, sockport)
        self.__taddr = (ip, time_port)
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
        self.__READBUFFER = b''
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.timeSock = socket(AF_INET, SOCK_DGRAM)
        self.datatype['Device'] = device
        self.sock.sendto(pickle.dumps(self.datatype), self.__addr)
        self.__TRRECV = None
        self.__TRSYNC = None
        self.__TCORR = None

    async def __timeSync(self):
        with socket(AF_INET, SOCK_DGRAM) as tmpServer:
            tmpDelay = []
            tmpServer.bind((''), self.__taddr[1])
            self.timeSock.sendto(b'\x0b', self.__taddr)
            if self.timeSock.recv(1) == b'\x0b':
                for i in range(1,20):
                    lT = datetime.now()
                    self.timeSock.sendto(i*b'\x0c',self.__taddr)
                    if tmpServer.recv(i) == i*b'\x0c':
                        tmpDelay += [(datetime.now() - lT).microseconds / 2]
                self.__TCORR = np.polynomial.Polynomial.fit(np.arange(1,20), tmpDelay)
                self.__TRRECV = pickle.loads(tmpServer.recv(53)) - timedelta(microseconds=self.__TCORR(53))
                self.__TRSYNC = datetime.now()
        
    async def __run(self):
        try:
            self.__READBUFFER += self.read_all()
            readoutRaw = np.array([ByteArray(dFrame).listMask(self.BUFFBYTES) for dFrame in self.__READBUFFER.split(b'\r\n')[:-1]]).T
            readout = [np.frombuffer(data.tobytes(), dtype).astype(dtype) for data, dtype in zip(readoutRaw, self.datatype.values())]
            if len(readout) > 1:
                self.__READBUFFER = self.__READBUFFER[self.__READBUFFER.rindex(b'\r\n')+2:] 
                msg = {'data':readout, 'timestamp': self.__TRRECV + timedelta(microseconds=(self.__TRSYNC - datetime.now()).microseconds - self.__TCORR(53+readoutRaw.nbytes))}
                self.sock.sendto(pickle.dumps(msg), self.__addr)
            if (datetime.now() - self.__TRRECV).minutes > 4:
                await self.__timeSync()
        except FileNotFoundError:
            if self.__ATTEMPTS > 5:
                self.cancel()
                return
            self.__ATTEMPTS += 1
            print('[SER-READER] Serial connection lost, trying to reconnect')
            self.open()    
        except Exception:
            pass   

    def start(self):
        self.__timer.start()
    def cancel(self):
        self.__timer.cancel()

class Packet_Manager():
    def __init__(self, reader_port=3001, time_port=2020, ws_address="127.0.0.1", ws_port=3000, dps=30) -> None:
        threadbuff = {}
        lock = Lock()
        addr = {}
        websocket = create_connection("ws://"+ws_address+":"+str(ws_port))
        reader_socket = socket(AF_INET, SOCK_DGRAM)
        reader_socket.bind(('',reader_port))
        self.__recv = Thread(target=Packet_Manager.run_receiver, args=(reader_socket, addr, lock, threadbuff,))
        self.__timeSync = Thread(target=Packet_Manager.run_time_sync, args=(time_port,))
        self.__sendTimer = RepeatTimer(1/dps, Packet_Manager.run_sender(lock, threadbuff, websocket))
        print('[PACKER] UDP socket ready')
    
    @staticmethod
    def run_time_sync(time_port: int):
        timeSock = socket(AF_INET, SOCK_DGRAM)
        sync_client = socket(AF_INET, SOCK_DGRAM)
        timeSock.bind((''), time_port)
        syncFlag = False
        syncAddr = None
        syncCount = 0
        while(True):
            data, address = timeSock.recvfrom(1)
            if data == b'\x0a' and not syncFlag:
                syncFlag = True
                syncAddr = (address[0], time_port)
            if syncFlag:
                sync_client.sendto(data, (syncAddr[0], syncAddr))
                syncCount += 1
                if syncCount == 20:
                    sync_client.sendto(pickle.dumps(datetime.now()), syncAddr)
                    syncFlag = False
                    syncCount = 0

    @staticmethod
    def run_receiver(reader_socket: socket, addr: dict, lock: Lock, threadbuff: dict):
        while(True):
            try:
                data, address = reader_socket.recvfrom(16384)
                if not address in addr.keys():
                    lock.acquire()
                    tmp = pickle.loads(data)
                    tmp_device = tmp.pop('Device')
                    addr[address] = tmp_device
                    threadbuff[tmp_device] = {'Data':[np.array([0].astype(dtype)) for dtype in tmp.values()], 'Keys':list(tmp.keys()), 'Known':False}
                    lock.release()
                    print('[PACKER] Registered ' + tmp_device)
                else:
                    lock.acquire()
                    tmp_data = pickle.loads(data)
                    threadbuff[addr[address]]['Data'] = [np.vstack((columData,tmpColumData)).astype(tmpColumData.dtype) for columData, tmpColumData in zip(threadbuff[addr[address]]['Data'], tmp_data)]
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
            res['data'] = [np.mean(colData[:-1]) for colData in dict_data['Data']]
            websocket.send(json.dumps(res))

    def start(self):
        self.__timeSync.start()
        self.__recv.start()
        self.__sendTimer.start()

    def cancel(self):
        self.__recv.join()
        self.__sendTimer.cancel()

