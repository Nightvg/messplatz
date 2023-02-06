from copy import deepcopy
import json
from datetime import datetime, date
from queue import Queue
from socket import AF_INET, SOCK_STREAM
from socket import error as SockErr
from socket import socket
from threading import Thread, Timer, Event
from time import sleep
from typing import Any
import logging

import ntplib
import pandas as pd
from PyQt5.QtGui import QTabletEvent
from PyQt5.QtWidgets import QWidget, QApplication
import numpy as np
from serial import Serial, serialutil
import serial.tools.list_ports as list_ports
from websocket import create_connection, WebSocket

module_logger = logging.getLogger('main.messplatz')
logging.basicConfig(filename=f'{date.today()}.log',filemode="a")

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
    def listMask(self, cmpList:list) -> list:
        buff = self
        def _part(li,s): 
            return [] if len(li)==0 \
            else [li] if len(s)==0 \
            else [li[:s[0]]] + _part(li[s[0]:], s[1:])
        res = []
        while len(buff) > 0:
            if len(self) <= sum(cmpList):
                res += _part(buff[:sum(cmpList)],cmpList)
            else:
                res += [_part(buff[:sum(cmpList)],cmpList)]
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
        self._SYNCFLAG = self._timeSync()
        self.logger = logging.getLogger('messplatz.Reader')
    def _timeSync(self) -> bool:
        try:
            tc = ntplib.NTPClient().request('de.pool.ntp.org', version=4)
            self._TSTART = datetime.fromtimestamp(tc.orig_time)
            self._TSYNC = datetime.fromtimestamp(tc.tx_time + tc.delay / 2)
            return True
        except Exception as e:
            self.logger.error(f'{e}')
            return False
    def _getTime(self) -> datetime:
        return datetime.now() - self._TSTART + self._TSYNC
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
        if self._SYNCFLAG:
            try:
                stamplist = []                
                self._READBUFFER += self.read_all() if not self._ISDEV else data
                vals = [
                    self._LCORR(dFrame) \
                    for dFrame in self._READBUFFER.split(b'\r\n')[:-1]
                ]
                corr_list = np.arange(len(vals))*1/2000
                if self._timeLast is None:
                    self._timeLast = datetime.now().timestamp()
                    stamplist = [
                        x.tobytes() for x in corr_list[::-1] + self._timeLast
                    ]
                else:
                    stamplist = [
                        x.tobytes() for x in corr_list + 1 + self._timeLast
                    ]
                    self._timeLast = np.frombuffer(stamplist[-1],np.float64)[0]
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
        else:
            self._SYNCFLAG = self._SAMEMACHINE and self._timeSync()
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
        sleep(1)
        self.timer.cancel()
        self.closeSocket()

class ReaderFactory:
    def createReader(**kwargs) -> Reader|None:
        try:
            if any([x in kwargs for x in ['port','baudrate', 'dps', 'serial']]):
                return SerialReader(**kwargs)
            elif any([x in kwargs for x in ['tablet']]):
                return TabletReader(**kwargs)
            else:
                return None
        except serialutil.SerialException as e:
            logging.warning(f'{e}')
            return ReaderFactory.createReader(**{**kwargs, 'dev':True})

class PacketManager():
    def __init__(
            self,
            datatype:dict[str,Any],
            name: str,
            ws_address="127.0.0.1",
            ws_port=3000,
            **kwargs
        ) -> None:      
        '''
        necessary arguments:
            datatype    : dictionary of name(s) and datatype(s) of the reader inputs
            name        : name of the device
        optional arguments:
            ws_address  : websocket address, default on the same machine
            ws_port     : websocket port, default 3000
            sockport    : internal port for data transmission, default 3001
            nows        : disables connection to websocket (no live charting)
        additional arguments:
            serial      : reader type serial, bool
            tablet      : reader type tablet, bool
            baudrate    : serial baudrate, default 500000
            dps         : dataframes per second, default 60
        '''
        self.logger = logging.getLogger('messplatz.PacketManager')
        self.dev = 'dev' in kwargs and kwargs['dev']
        self.nows = self.dev or ('nows' in kwargs and kwargs['nows'])
        if not self.dev:
            try:
                self.ws = create_connection("ws://"+ws_address+":"+str(ws_port))
            except ConnectionRefusedError as e:
                self.logger.warning(f'{e}')
                self.ws = WebSocket()
                self.dev = True
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
    
    def getDataFrame(self) -> pd.DataFrame|None:
        return self._writerThread.df if self._writerThread.is_alive() else None
    def resetDataFrame(self) -> None:
        self._writerThread.df = self.df
    def close(self) -> None:
        self.reader.stop()
        self._serverThread.join()
        self._writerThread.join()
    def start(self) -> None:
        self._serverThread.start()
        self._writerThread.start()
        self.reader.run()

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
            with socket(AF_INET, SOCK_STREAM) as sock:
                #sock.setblocking(False)
                sock.bind(('', self.port))
                sock.listen(1)
                conn, _  = sock.accept()
                data = b''
                while not self.events['endSend'].is_set():
                    try:
                        tmp = conn.recv(CtrlFlags.MAXB)
                        data += tmp
                        byteSize = not len(data) % sum(self.BUFFBYTES)
                        if len(tmp) < CtrlFlags.MAXB and byteSize:  
                            #tmpLen = len(data)  
                            #self.logger.info(f'received {tmpLen} bytes')
                            iniSp = list(zip(*ByteArray(data).listMask(self.BUFFBYTES)))
                            res = [
                                np.frombuffer(b''.join(d), dtype).tolist() \
                                for d,dtype in zip(iniSp,self.datatype.values())
                            ] 
                            self.q.put(list(zip(*res)))
                            if not self.nows:
                                res = np.mean(res, axis=1).tolist()[:-1] if \
                                    len(res[0]) > 1 else res[:-1]
                                self.ws.send(
                                    json.dumps(
                                        {
                                            'names': list(self.datatype.keys())[:-1], 
                                            'device': self.device,
                                            'data': res
                                        }
                                    )
                                )
                            data = []
                    except SockErr as e:
                        self.logger.error(f'{e}')
                        continue
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
            while not (self.q.empty() and self.events['endSend'].is_set()):
                if not self.q.empty():
                    data = self.q.get()
                    tmp = pd.DataFrame(
                        data,
                        columns=self.df.columns
                    ).astype(self.datatype)
                    self.logger.info(f'received {len(tmp)} rows of data')
                    length = len(self.df)
                    if length == 0:
                        with open('file.csv','a') as file:
                            file.write(tmp.to_csv())
                        self.df = tmp
                    if length > 0:
                        with open('file.csv','a') as file:
                            file.write(tmp.to_csv(header=False))
                        self.df = pd.concat([self.df, tmp], ignore_index=True)
            self.events['endWork'].set()
            return True
