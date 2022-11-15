import asyncio
import json
import logging
import pickle
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime, timedelta
from socket import AF_INET, SOCK_STREAM
from socket import error as SockErr
from socket import socket
from threading import Timer
from typing import Any, Iterable
from multiprocessing import Process, Lock

import numpy as np
from serial import Serial
from websocket import WebSocket, create_connection

class CtrlFlags():
    SYNC = b'\x0b'
    SMMH = b'\xbb'
    MAXB = 65536

class ByteArray(bytes):
    def __new__(cls, byte=b''):
        return super().__new__(cls, byte)
    def listMask(self, cmpList:list) -> list:
        return (f:=lambda l,s: 
            [] if len(l)==0
            else [l] if len(s)==0
            else [l[:s[0]]] + f(l[s[0]:], s[1:]))(self, cmpList)
        
class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class Data(np.ndarray):
    def __new__(cls, inarr, dtype=None, name=''):
        obj = np.asarray(inarr, dtype=dtype).view(cls)
        obj.name = name
        return obj
    def __array_finalize__(self, obj):
        if obj is None: return
        self.name = getattr(obj, 'name', '')
    def __eq__(self, other: Iterable[Any]) -> bool:
        return np.array_equal(self, np.array(other, dtype=self.dtype))
    def __add__(self, obj: Any) -> Any:
        return Data(np.append(self, np.array(obj, dtype=self.dtype)), dtype=self.dtype, name=self.name)
    def __iadd__(self, i: Any):
        self = self.__add__(i)
        return self

class Datas(tuple):
    def __new__(cls, __iterable: Iterable[Data] = ...):
        obj = super().__new__(cls, [Data(x, dtype=x.dtype, name=x.name) if isinstance(x, Data) else Data(x, dtype=x.dtype) if isinstance(x, np.ndarray) else np.array(x) for x in __iterable]) 
        obj._dtlen = sum([x.itemsize for x in obj])
        return obj
    def __iadd__(self, s: Iterable[Any]):
        if len(self) == len(s):
            self = Datas([x + np.array(y, dtype=x.dtype) for x,y in zip(self, s)])
        return self
    def __contains__(self, __x: Data) -> bool:
        return super().__contains__(__x)
    def dtypes(self) -> list:
        return [x.dtype for x in self]
    def toBytes(self) -> bytes:
        return b''.join([x.tobytes() for x in self])
    def fromBytes(self, byte: bytes = ...) -> Any:
        tList = self.dtypes()
        if len(byte) % self._dtlen == 0:
            mask = [x.itemsize*len(byte)//self._dtlen for x in tList]
            return Datas([np.frombuffer(x,y) for x,y in zip(ByteArray(byte).listMask(mask), tList)])
    def getDict(self):
        return {x.name: x.dtype for x in self}
    def getMean(self):
        return np.mean(self, axis=1)

class Device:
    def __init__(self, d: dict[str, Any] | Datas = ..., name: str = ...) -> None:
        self.name = name
        self.datas = Datas([Data([], name=n, dtype=dt) for n,dt in d.items()]) if type(d) == dict else d
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Device) and self.datas.dtypes() == __o.datas.dtypes() and self.name == __o.name
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    def __contains__(self, d: Data) -> bool:
        return d in self.datas
    def __len__(self) -> int:
        return len(self.datas)
    def __str__(self) -> str:
        return self.name
    def __dict__(self):
        return 
    def toBytes(self):
        return self.datas.toBytes()
    def getDict(self):
        return self.datas.getDict()
    def pop(self):
        return Device(d=Datas([x[-1] for x in self.datas]), name=self.name)

class Reader(Serial):    
    def __init__(self, port="COM3", baudrate=500000, ip="127.0.0.1", sockport=3001, time_port=2020, dps=60, device='microcontroller', datatype:dict={'EMG1':np.float32, 'EMG2':np.float32, 'ECG':np.float32, 'BR':np.float32, 'EDA':np.float32}, **kwargs):
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
        if not 'dev' in kwargs:
            #see microcontroller for baudrate, port could change on differnt devices
            super().__init__(port=port, baudrate=baudrate) 
            #enlarge input buffer
            self.set_buffer_size(rx_size=1024*(2**4), tx_size=1024) 
            self.reset_input_buffer()
        self.__timer = RepeatTimer(1/dps, self.loop)
        self.__addr = (ip, sockport)
        self.__taddr = (ip, time_port)
        self.datatype = datatype  
        self.MAX_ATTEMPS = 5
        self.__ATTEMPTS = 0
        #number of bytes to read
        self.BUFFBYTES = [np.dtype(x).itemsize for x in self.datatype.values()]
        #constant value for incorrect read
        self.WRONGREAD = sum(self.BUFFBYTES)*b'\x00'

        #initialize readbuffer as byte type due to byte reading from pyserial
        self.__READBUFFER = b''
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.datatype['Device'] = device
        self.sock.connect(self.__addr)
        self.sock.send(pickle.dumps(self.datatype))
        #Flags and anonymous methods
        self.__SAMEMACHINE = ip == '127.0.0.1'
        self.__SYNCFLAG = self.__SAMEMACHINE
        self.__TRRECV = None
        self.__TRSYNC = None
        self.__TCORR = None
        self.__ISDEV = True if 'dev' in kwargs else False
        self.__LCORR = lambda x : x if len(x) == sum(self.BUFFBYTES) else self.WRONGREAD

    def __timeSync(self) -> bool:
        try:
            with socket(AF_INET, SOCK_STREAM) as timeSync:
                tmpDelay = []
                timeSync.connect(self.__taddr)
                timeSync.send(CtrlFlags.SYNC)
                if timeSync.recv(1) == CtrlFlags.SYNC:
                    for i in range(1,21):
                        lT = datetime.now()
                        timeSync.send(i*b'\x0c')
                        if timeSync.recv(i) == i*b'\x0c':
                            tmpDelay += [(datetime.now() - lT).microseconds / 2]
                    self.__TCORR = np.polynomial.Polynomial.fit(np.arange(1,21), tmpDelay)
                    self.__TRRECV = pickle.loads(timeSync.recv(80)) - timedelta(microseconds=self.__TCORR(53))
                    self.__TRSYNC = datetime.now()
            return True
        except Exception as e:
            print(f'[Reader][Timesync][ERROR] {e}')
            return False    

    def loop(self, data=b'') -> None:
        if self.__SYNCFLAG:
            try:
                self.__READBUFFER += self.read_all() if not self.__ISDEV else data
                readout = [[np.frombuffer(data, dtype) for data, dtype in zip(ByteArray(self.__LCORR(dFrame)).listMask(self.BUFFBYTES),self.datatype.values())] for dFrame in self.__READBUFFER.split(b'\r\n')[:-1]]
                self.__READBUFFER = self.__READBUFFER[self.__READBUFFER.rindex(b'\r\n')+2:] 
                msg = pickle.dumps({'data':readout, 'timestamp': self.__getTime()}) #TODO -> timedelta
                self.sock.send(msg)
                #if not self.__SAMEMACHINE and (datetime.now() - self.__TRRECV).minutes > 4:
                #    self.__SYNCFLAG = False
            except FileNotFoundError:
                if self.__ATTEMPTS > 5:
                    self.cancel()
                    self.__timer.cancel()
                    return
                self.__ATTEMPTS += 1
                print('[SER-READER] Serial connection lost, trying to reconnect')
                self.open()    
            except SockErr as e:
                print(f'[Reader][TCP-ERROR] {e}')
                self.sock.connect(self.__addr)
            except Exception as e:
                print(f'[Reader][ERROR] {e}')
        else:
            self.__SYNCFLAG = self.__SAMEMACHINE and self.__timeSync()

    def __getTime(self) -> datetime:
        return self.__TRRECV + timedelta(microseconds=(self.__TRSYNC - datetime.now()).microseconds - self.__TCORR(53+len(self.__READBUFFER))) if not self.__SAMEMACHINE else datetime.now()

    def start(self):
        self.write(b'2') #TODO -> Startbyte notieren, ausprobieren
        self.__timer.start()

    def cancel(self):
        self.write(b'0') #TODO -> Endbyte notieren
        self.__timer.cancel()


class TimeSync(RepeatTimer):
    def __init__(self, timePort: int, dps: int) -> None:
        self.timePort = timePort
        self.timeSock = socket(AF_INET, SOCK_STREAM)
        self.timeSock.bind(('', self.timePort))
        self.syncFlag = False
        self.syncCount = 0
        super().__init__(1/dps, self.loop)

    def loop(self):
        self.timeSock.listen()
        conn, _ = self.timeSock.accept()
        with conn:
            self.syncFlag = True if conn.recv(20) == CtrlFlags.SYNC else False
            if self.syncFlag:
                conn.send(CtrlFlags.SYNC)
            while self.syncFlag:
                conn.send(conn.recv(20))
                self.syncCount += 1
                if self.syncCount == 20:
                    conn.send(pickle.dumps(datetime.now()))
                    self.syncFlag = False
                    self.syncCount = 0


class PacketReceiver:
    def __init__(self, readerSocket: socket = ..., lock: Lock = ..., buffer = dict[str, Device]) -> None:
        self.__readerSocket = readerSocket
        self.__readerSocket.listen()
        self.addr = {}
        self.buffer = buffer
        self._lock = lock
        self._proc = Process(target=self.loop)
    def loop(self):
        while True:
            try:
                conn, address = self.__readerSocket.accept()
                with conn:
                    data = conn.recv(CtrlFlags.MAXB)
                    if not address in self.addr.keys():
                        tmp = pickle.loads(data)
                        nDevice = Device(tmp['Data'], name=tmp['Device'])
                        self.addr[address] = nDevice
                        self._lock.acquire()
                        self.buffer[nDevice] = nDevice
                        self._lock.release()
                        print(f'[PReceiver] Registered {nDevice}')
                    else:
                        tmpD : Device = self.addr[address]
                        self._lock.acquire()
                        self.buffer[tmpD].datas += tmpD.datas.fromBytes(data)
                        self._lock.release()
            except Exception as e:
                print(f'[PReceiver][ERROR] {e}')
    def cancel(self):
        self._proc.join()
    def start(self):
        self._proc.start()

class PacketSender(RepeatTimer):
    def __init__(self, websocket: WebSocket = ..., dps: int = ..., lock: Lock = ..., buffer = dict[str, Device]) -> None:
        self._websocket = websocket
        self._lock = lock
        self.buffer = buffer
        super().__init__(1/dps, self.loop)

    def loop(self):
        try:
            self._lock.acquire()
            for key, device in self.buffer.items():
                self._websocket.send(json.dumps(device.datas.getMean().tolist()))
                self.buffer[key] = device.pop()
            self._lock.release() 
        except Exception as e:
            print(f'[PSender][ERROR] {e}')

class SenderManager():
    pass

class ReceiverManager():
    pass

class ReaderManager():
    pass

class PacketManager():
    def __init__(self, reader_port=3001, time_port=2020, ws_address="127.0.0.1", ws_port=3000, dps=30) -> None:
        threadbuff = {}
        lock = Lock()
        readerSocket = socket(AF_INET, SOCK_STREAM)
        readerSocket.bind(('',reader_port))
        self.__recv = PacketReceiver(readerSocket=readerSocket, lock=lock, buffer=threadbuff, dps=4*dps)
        websocket = create_connection("ws://"+ws_address+":"+str(ws_port))
        self.__send = PacketSender(lock=lock, buffer=threadbuff, websocket=websocket, dps=dps)
        self.__time = TimeSync(timePort=time_port, dps=dps)
        self.__reader = []
        print(f'[PManager] UDP socket ready')

    def attachReader(self, *args, **kwargs):
        self.__reader.append(Reader(*args, **kwargs))

    # def attachReceiver(self, *args, **kwargs):
    #     self.__receiver.append(PacketReceiver(*args, **kwargs))

    # def attachListener(self, *args, **kwargs):
    #     self.__sender.append(PacketSender(*args, **kwargs))
    # TODO -> Struktur auf Manager -> Unit ändern

    def start(self):
        self.__time.start()
        self.__recv.start()
        self.__send.start()
        for r in self.__reader:
            r.start()

    def cancel(self):
        self.__recv.cancel()
        self.__send.cancel()
        self.__time.cancel()
        for r in self.__reader:
            r.cancel()

