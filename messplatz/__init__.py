from copy import deepcopy
import json
from datetime import datetime, date, timedelta
from multiprocessing import Pool
from queue import Queue
from socket import AF_INET, SOCK_STREAM
from socket import error as SockErr
from socket import socket
from threading import Thread, Timer, Event
from time import sleep
from typing import Any
import logging
import requests
import os

import pandas as pd
from PyQt5.QtGui import QTabletEvent
from PyQt5.QtWidgets import QWidget, QApplication
import numpy as np
from serial import Serial, serialutil
import serial.tools.list_ports as list_ports
import flask
from scipy.signal import iirdesign, lfilter

module_logger = logging.getLogger('main.messplatz')
logpath = os.path.join(os.path.dirname(__file__),'../logs/')
logging.basicConfig(filename=f'{logpath}{date.today()}.log',filemode="a")

class CtrlFlags():
    SYNC = b'\x0b'
    SMMH = b'\xbb'
    DONE = b'\x00'
    FNSH = b'\xff'
    PING = b'\x30'
    MAXB = 8192

class ByteArray(bytes):
    def __new__(cls, byte=b''):
        return super().__new__(cls, byte)
    def listMask(self, cmpList:list) -> list[bytes] | list[list[bytes]]:
        buff = self
        def _part(li,s): 
            return [] if len(li)==0 \
            else [li] if len(s)==0 \
            else [li[:s[0]]] + _part(li[s[0]:], s[1:])
        res = []
        while len(buff) > 0:
            res += [_part(buff[:sum(cmpList)], cmpList)]
            buff = buff[sum(cmpList):]
        return res
        
class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)
                
class Reader:
    def __init__(
            self,
            events: dict[str: Event],
            sockport: int = 3001,
            ip: str = '127.0.0.1', 
            taddr: tuple[str,int] = ('',0),
            **kwargs
        ) -> None:
        self._addr = (ip, sockport)
        self._taddr = taddr
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.MAX_ATTEMPS = 5
        self._ATTEMPTS = 0
        self.events = events
        self.logger = logging.getLogger('messplatz.Reader')
    def connectSocket(self) -> None:
        self.sock.connect(self._addr)
    def closeSocket(self) -> None:
        self.events['endSend'].set()
        self.events['endWork'].wait(timeout=None)
        self.sock.close()

class Tablet(QWidget):
    def __init__(self, app: QApplication, sock: socket, parent=None):
        super().__init__(parent)
        # Resizing the sample window to full desktop size:
        frame_rect = app.desktop().frameGeometry()
        width, height = frame_rect.width(), frame_rect.height()
        self.resize(width, height)
        self.move(-9, 0)
        self.setWindowTitle("Sample Tablet Event Handling")
        self.sock = sock
    def tabletEvent(self, tabletEvent : QTabletEvent):
        try:
            self.sock.sendall(
                np.int16(tabletEvent.pressure()*1000).tobytes() + \
                np.float64(datetime.now().timestamp()).tobytes() + \
                b'\r\n'
            )
            #TODO ändern
            tabletEvent.accept()
        except Exception as e:
            logging.getLogger('messplatz.Tablet').error(f'{e}')


class TabletReader(Reader):
    def __init__(self, **kwargs) -> None:
        super().__init__(sockport=kwargs['sockport'])
    def run(self):
        super().connectSocket()
        self.app = QApplication([])
        self.mainform = Tablet(self.app, self.sock)
        self.mainform.show()
        self.app.exec_()
    def stop(self):
        self.app.exit()
        super().closeSocket()
    

class SerialReader(Serial, Reader):    
    def __init__(
            self, 
            baudrate=500000, 
            dps=30, 
            datatype:dict={
                'EMG1':np.float32,
                'EMG2':np.float32,
                'ECG':np.float32,
                'BR':np.float32,
                'EDA':np.float32
            },
            **kwargs
        ):
        """
        Initialize the serial reader.

        Arguments:
            baudrate    : datatransferrate in signes per second, usually bits
            ip          : ipv4 address of packer server
            sockport    : portnumber of packer server
            dps         : dataframes per second
            datatype    : list of types of inputdata, has to be the same type thoughout
                          the set of inputs
        """
        if 'dev' not in kwargs:
            #see microcontroller for baudrate, port could change on differnt devices
            Reader.__init__(self, **kwargs)
            for comport in list_ports.comports():
                try:
                    Serial.__init__(
                        self, 
                        port=comport.device,
                        baudrate=baudrate,
                        timeout=0.1
                    ) 
                    self.write(CtrlFlags.PING)
                    if self.read(2) == b'OK':
                        break
                except Exception as e:
                    self.logger.error(f'{e}')
            #enlarge input buffer
            self.set_buffer_size(rx_size=1024*(2**4), tx_size=1024) 
            self.reset_input_buffer()
        else:
            Serial.__init__(self)
            Reader.__init__(self, **kwargs)
        self.timer = RepeatTimer(1/dps, self.loop)
        self.datatype = datatype  
        #number of bytes to read
        BUFFBYTES = sum([np.dtype(x).itemsize for x in self.datatype.values()])
        #constant value for incorrect read
        self.WRONGREAD = BUFFBYTES*b'\x00'
        #initialize readbuffer as byte type due to byte reading from pyserial
        self._READBUFFER = b''
        self._SAMEMACHINE = 'ip' not in kwargs or kwargs['ip'] == '127.0.0.1'
        #Flags and anonymous methods
        self._ISDEV = 'dev' in kwargs and kwargs['dev']
        self._LCORR = lambda x : x if len(x) == BUFFBYTES else self.WRONGREAD
        self._ROWS = 0
        self._timeLast = None
    def loop(self, data=b'') -> None:
        try:
            stamplist = []                
            self._READBUFFER += self.read_all() if not self._ISDEV else data
            if self._timeLast is None:
                self._timeLast = datetime.now()
            vals = [
                self._LCORR(dFrame) \
                for dFrame in self._READBUFFER.split(b'\r\n')[:-1]
            ]
            stamplist = [
                np.float64(
                    (self._timeLast + timedelta(microseconds=x)).timestamp()
                ).tobytes()\
                for x in range(0,len(vals)*500,500)
            ]
            self._timeLast += timedelta(microseconds=len(vals)*500)
            if len(self._READBUFFER) > 0:
                self._READBUFFER = self._READBUFFER[
                    self._READBUFFER.rindex(b'\r\n')+2:
                ] 
            msg = b''.join([x + y for x,y in zip(vals,stamplist)])
            self._ROWS = self._ROWS + len(vals)
            self.logger.info(
                f'sent {len(vals)} rows of data, total of {len(msg)} bytes'
            )
            while len(msg) > CtrlFlags.MAXB:
                self.sock.send(msg[:CtrlFlags.MAXB])
                msg = msg[CtrlFlags.MAXB:]
            self.sock.send(msg)
        except FileNotFoundError as e:
            if self._ATTEMPTS > 5:
                self.logger.error('Could not reconnect, shuting down')
                self.stop()
                return
            self._ATTEMPTS += 1
            self.logger.warning(f'{e}')
            self.open()    
        except Exception as e:
            self.logger.error(f'{e}')

    def run(self):
        self.logger.info('starting connection...')
        if not self._ISDEV:
            self.write(b'2')
        self.connectSocket()
        self.timer.start()
    def stop(self):
        self.logger.info('stopping connection...')
        if not self._ISDEV:
            self.write(b'1') 
        sleep(3)
        self.timer.cancel()
        self.closeSocket()

class ReaderFactory:
    def createReader(**kwargs) -> Reader|None:
        res = None
        try:
            if any([x in kwargs for x in ['port','baudrate', 'dps', 'serial']]):
                res = SerialReader(**kwargs)
            elif any([x in kwargs for x in ['tablet']]):
                res = TabletReader(**kwargs)
            else:
                #TODO new Readertypes
                res = None
        except serialutil.SerialException as e:
            logging.warning(f'{e}')
        except Exception as e:
            logging.warning(f'{e}')
        finally:
            return res

class Manager():
    def __init__(
            self,
            datatype:dict[str,Any],
            name: str,
            **kwargs
        ) -> None:      
        '''
        necessary arguments:
            datatype    : dictionary of name(s) and datatype(s) of the reader inputs
            name        : name of the device
        optional arguments:
            ip          : neccessary if receiving part is not on the local machine
            sockport    : internal port for data transmission, default 3001
            filter      : list of filters (one for each datatype)
        additional arguments:
            serial      : reader type serial, bool
            tablet      : reader type tablet, bool
            baudrate    : serial baudrate, default 500000
            dps         : dataframes per second, default 60
        '''
        self.logger = logging.getLogger('messplatz.PacketManager')
        self.dev = 'dev' in kwargs and kwargs['dev']
        self.api = flask.Flask(__name__)
        self.ip = kwargs['ip'] if 'ip' in kwargs else 'localhost'
        self.filters = kwargs['filter'] if 'filter' in kwargs else \
            {x: {'b':[1], 'a':[1]} for x in datatype.keys()}
        self.datatype = datatype
        self.device = name
        self.events = {'endSend':Event(), 'endWork':Event()}
        self.port = kwargs['sockport'] if 'sockport' in kwargs else 3001
        self.reader = ReaderFactory.createReader(
            **{
                **kwargs,
                'events': self.events,
                'datatype': deepcopy(datatype),
                'sockport': self.port
            }
        )
        self.interval = self.reader.timer.interval \
            if isinstance(self.reader, SerialReader) else 1
        self.datatype['timestamp'] = np.float64
        self.BUFFBYTES = [np.dtype(x).itemsize for x in self.datatype.values()]
        self.df = pd.DataFrame(
            np.empty(
                0, dtype=[(key, np.dtype(value)) for key, value in datatype.items()]
            )
        )
        self.q = Queue()
        self._serverThread = self.Read(**self.__dict__)
        self._writerThread = self.Write(**self.__dict__)

        @self.api.put('/filter')
        def filter(self):
            pass_args = flask.request.get_json()
            b,a = iirdesign(**pass_args)
            self.filters[pass_args['name']] = {'b': b, 'a': a}

    def close(self) -> None:
        self.reader.stop()
        self._serverThread.join()
        self._writerThread.join()
    def start(self) -> None:
        self._serverThread.start()
        self._writerThread.start()
        self.reader.run()
        self.api.run(port=8080)

    class Read(Thread):
        def __init__(self, **kwargs):
            super().__init__(target=self._read)
            self.__dict__.update(
                {
                    key: value for key, value in kwargs.items() if key[0] != '_'
                }
            )
            self.logger = logging.getLogger('messplatz.Read')
        def _read(self):
            def format(elems):
                if len(elems) > 1:
                    elems = zip(*elems)
                    return [
                        np.frombuffer(b''.join(d), dtype).tolist() \
                        for d,dtype in zip(elems,self.datatype.values())
                    ]
                return [
                    np.frombuffer(d, dtype).tolist() \
                    for d,dtype in zip(elems[0],self.datatype.values())
                ]
            with socket(AF_INET, SOCK_STREAM) as sock:
                #sock.setblocking(False)
                sock.bind(('', self.port))
                sock.listen(1)
                conn, _  = sock.accept()
                data = b''

                with Pool(4) as pool:
                    while not self.events['endSend'].is_set():
                        tmp = conn.recv(CtrlFlags.MAXB)
                        data += tmp
                        if len(data) > 0 and (len(data) % sum(self.BUFFBYTES)) == 0:  
                            try:
                                res = format(ByteArray(data).listMask(self.BUFFBYTES))
                                self.q.put(res)              
                                pool.apply_async(
                                    _asyncSend, 
                                    args=(
                                        self.device,
                                        list(self.datatype.keys())[:-1],
                                        self.ip,
                                        res,
                                    )
                                )
                                data = b''
                            except SockErr as e:
                                self.logger.error(f'{e}')
                                continue
                            except TypeError as e:
                                self.logger.error(f'Wrong Type: {e}')
                            except Exception as e:
                                #self.events['endWork'].set()                
                                self.logger.error(f'{e}')
            return False
    class Write(Thread):
        def __init__(self, **kwargs):
            super().__init__(target=self._write)
            self.__dict__.update(
                {
                    key: value for key, value in kwargs.items() if key[0] != '_'
                }
            )
            self.logger = logging.getLogger('messplatz.Write')
        def _write(self) -> bool:
            init = False
            path = os.path.dirname(__file__)
            filepath = os.path.join(path,f'../data/{date.today()}.csv')
            while not (self.q.empty() and self.events['endSend'].is_set()):
                if not self.q.empty():
                    with open(filepath,'a') as file:
                        data = list(zip(*self.q.get()))
                        tmp = pd.DataFrame(
                            columns=self.df.columns
                        ).astype(self.datatype)
                        for ind,i in enumerate(data):
                            tmp.loc[ind] = i
                        self.logger.info(f'received {len(data)} rows of data')
                        if not init:
                            file.write(tmp.to_csv(index=False))
                            init = True
                        else:
                            file.write(tmp.to_csv(header=False, index=False))
            self.events['endWork'].set()
            return True

def _asyncSend(device, names, ip, datas):
    try:
        requests.put(
            f'http://{ip}/data',
            json={
                'names': names, 
                'device': device,
                'data': datas[:-1]
            },
            headers={
                'connection': 'close'
            },
            stream=False,
            timeout=0.10
        )
    except Exception as e:
        print(e)
