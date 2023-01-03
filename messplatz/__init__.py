from copy import deepcopy
import json
import pickle
from datetime import datetime, timedelta
from queue import Queue
from socket import AF_INET, SOCK_STREAM
from socket import error as SockErr
from socket import socket
from threading import Thread, Timer, Event
from typing import Any
import logging

import ntplib
import pandas as pd
from PyQt5.QtGui import QTabletEvent
from PyQt5.QtWidgets import QWidget, QApplication
import numpy as np
from serial import Serial
from websocket import create_connection

module_logger = logging.getLogger('main.messplatz')

class CtrlFlags():
    SYNC = b'\x0b'
    SMMH = b'\xbb'
    DONE = b'\x00'
    FNSH = b'\xff'
    MAXB = 8192

class ByteArray(bytes):
    def __new__(cls, byte=b''):
        return super().__new__(cls, byte)
    def listMask(self, cmpList:list) -> list:
        return (f:=lambda li,s: 
            [] if len(li)==0
            else [li] if len(s)==0
            else [li[:s[0]]] + f(li[s[0]:], s[1:]))(self, cmpList)
        
class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

# class TimeSync:
#     def __init__(self, timePort: int) -> None:
#         self._syncFlag = False
#         self._syncCount = 0
#         self._proc = multiprocessing.Process(target=self.loop, args=(timePort,))
#     def loop(self, timePort):
#         self.timeSock = socket(AF_INET, SOCK_STREAM)
#         self.timeSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
#         self.timeSock.bind(('', timePort))
#         self.timeSock.listen(1)
#         while True:
#             conn, _ = self.timeSock.accept()
#             i = 0
#             while i < 20:
#                 print(i)
#                 data = conn.recv(1000)
#                 if data == CtrlFlags.SYNC:
#                     conn.sendall(pickle.dumps(datetime.now()))
#                 else:
#                     conn.sendall(data)
#                 i += 1
#     def start(self):
#         self._proc.start()
#     def kill(self):
#         self._proc.kill()
#         self.timeSock.close()
                    
class Reader:
    def __init__(
            self,
            event: Event,
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
        self.event = event
        self._SYNCFLAG = self._timeSync()
        self.logger = logging.getLogger('messplatz.Reader')
    def _timeSync(self) -> bool:
        try:
            tc = ntplib.NTPClient().request('de.pool.ntp.org', version=4)
            self._TSTART = datetime.fromtimestamp(tc.orig_time)
            self._TSYNC = datetime.fromtimestamp(tc.tx_time + tc.delay / 2)
            return True
        except Exception as e:
            print(e)
            return False
    def _getTime(self) -> datetime:
        return datetime.now() - self._TSTART + self._TSYNC
    def connectSocket(self):
        self.sock.connect(self._addr)
    def closeSocket(self):
        self.sock.sendall(CtrlFlags.FNSH)
        self.event.wait(timeout=None)
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
                pickle.dumps(
                    {
                        'data': int(tabletEvent.pressure()*1000),
                        'timestamp':datetime.now()}
                )
            )
            tabletEvent.accept()
        except Exception as e:
            print(f'[TABLET] {e}')


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
            port="COM3", 
            baudrate=500000, 
            dps=60, 
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
            port        : serialport to retrieve data from
            baudrate    : datatransferrate in signes per second, usually bits
            ip          : ipv4 address of packer server
            sockport    : portnumber of packer server
            dps         : dataframes per second
            datatype    : list of types of inputdata, has to be the same type thoughout
                          the set of inputs
        """
        if 'dev' not in kwargs:
            #see microcontroller for baudrate, port could change on differnt devices
            Serial.__init__(self, port=port, baudrate=baudrate) 
            Reader.__init__(self, **kwargs)
            #enlarge input buffer
            self.set_buffer_size(rx_size=1024*(2**4), tx_size=1024) 
            self.reset_input_buffer()
        else:
            Serial.__init__(self)
            Reader.__init__(self, **kwargs)
        self.timer = RepeatTimer(1/dps, self.loop)
        self.datatype = datatype  
        #number of bytes to read
        self.BUFFBYTES = [np.dtype(x).itemsize for x in self.datatype.values()]
        #constant value for incorrect read
        self.WRONGREAD = sum(self.BUFFBYTES)*b'\x00'
        #initialize readbuffer as byte type due to byte reading from pyserial
        self._READBUFFER = b''
        self._SAMEMACHINE = 'ip' not in kwargs or kwargs['ip'] == '127.0.0.1'
        #Flags and anonymous methods
        self._ISDEV = 'dev' in kwargs and kwargs['dev']
        self._LCORR = lambda x : x if len(x) == sum(self.BUFFBYTES) else self.WRONGREAD
        self._ROWS = 0
    def loop(self, data=b'') -> None:
        if self._SYNCFLAG:
            try:
                self._READBUFFER += self.read_all() if not self._ISDEV else data
                vals = [
                    ByteArray(self._LCORR(dFrame)).listMask(self.BUFFBYTES) \
                    for dFrame in self._READBUFFER.split(b'\r\n')[:-1]
                ]
                readout = [
                    np.frombuffer(data, dtype).tolist() for data, dtype in \
                    zip([b''.join(a) for a in zip(*vals)],self.datatype.values())
                ]
                if len(self._READBUFFER) > 0:
                    self._READBUFFER = self._READBUFFER[
                        self._READBUFFER.rindex(b'\r\n')+2:
                    ] 
                msg = pickle.dumps({'data':readout, 'timestamp': self._getTime()})
                self._ROWS = self._ROWS + len(vals)
                self.logger.info(
                    f'sent {len(vals)} rows of data, total of {len(msg)} bytes'
                )
                while len(msg) > CtrlFlags.MAXB:
                    self.sock.sendall(msg[:CtrlFlags.MAXB])
                    msg = msg[CtrlFlags.MAXB:]
                self.sock.sendall(msg)
                self.sock.sendall(CtrlFlags.DONE)
            except FileNotFoundError:
                if self._ATTEMPTS > 5:
                    self.stop()
                    return
                self._ATTEMPTS += 1
                print('[SER-READER] Serial connection lost, trying to reconnect')
                self.open()    
            except Exception as e:
                print(f'[Reader][ERROR] {e}')
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
            self.write(b'0') 
        self.timer.cancel()
        self.timer.join()
        self.closeSocket()

class ReaderFactory:
    def createReader(**kwargs) -> Reader:
        if any([x in kwargs for x in ['port','baudrate', 'dps', 'serial']]):
            return SerialReader(**kwargs)
        if any([x in kwargs for x in ['tablet']]):
            return TabletReader(**kwargs)

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
        additional arguments:
            serial      : reader type serial, bool
            tablet      : reader type tablet, bool
            port        : serial port, default \'COM3\'
            baudrate    : serial baudrate, default 500000
            dps         : dataframes per second, default 60
        '''
        if 'dev' not in kwargs:
            self.ws = create_connection("ws://"+ws_address+":"+str(ws_port))
        self.logger = logging.getLogger('messplatz.PacketManager')
        self.datatype = datatype
        self.device = name
        self.event = Event()
        self.port = kwargs['sockport'] if 'sockport' in kwargs else 3001
        self.reader = ReaderFactory.createReader(
            **{
                **kwargs,
                'event': self.event,
                'datatype': deepcopy(datatype),
                'sockport': self.port
            }
        )
        self.interval = self.reader.timer.interval \
            if isinstance(self.reader, SerialReader) else 1
        self.datatype['timestamp'] = object
        self.df = pd.DataFrame(
            np.empty(
                0, dtype=[(key, np.dtype(value)) for key, value in datatype.items()]
            )
        )
        self.q = Queue()
        self.dev = 'dev' in kwargs and kwargs['dev']
        self._serverThread = self.Read(**self.__dict__)
        self._writerThread = self.Write(**self.__dict__)
    
    def close(self) -> None:
        self.reader.stop()
        self._serverThread.join()
        self._writerThread.join()
    def start(self) -> None:
        self._serverThread.start()
        self._writerThread.start()
        self.reader.run()
        #print('t')

    class Read(Thread):
        def __init__(self, **kwargs):
            super().__init__(target=self._read, daemon=True)
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
                data = []
                while not self.event.is_set():
                    try:
                        tmp = conn.recv(CtrlFlags.MAXB)
                        data.append(tmp)
                        if tmp == CtrlFlags.FNSH:
                            self.event.set()
                            break
                        if tmp == CtrlFlags.DONE:  
                            tmpLen = len(b''.join(data[:-1]))          
                            self.logger.info(f'received {tmpLen} bytes')
                            data = pickle.loads(b''.join(data[:-1]))
                            self.q.put(data)
                            if not self.dev:
                                self.ws.send(
                                    json.dumps(
                                        {
                                            'names': list(self.datatype.keys())[:-1], 
                                            'device': self.device,
                                            'data':np.mean(
                                                data['data'], axis=1
                                            ).tolist()
                                        }
                                    )
                                )
                            data = []
                    except SockErr as e:
                        self.logger.error(f'{e}')
                        continue
                    except Exception as e:
                        self.event.set()                
                        self.logger.error(f'{e}')
            return False
    class Write(Thread):
        def __init__(self, **kwargs):
            super().__init__(target=self._write, daemon=True)
            self.__dict__.update(
                {
                    key: value for key, value in kwargs.items() if key[0] != '_'
                }
            )
            self.logger = logging.getLogger('messplatz.Write')
        def _write(self) -> bool:
            while not self.event.is_set() or not self.q.empty():
                if not self.q.empty():
                    data = self.q.get()
                    tmp = None
                    tmpStmp = None
                    if type(data['data'][0]) != list:
                        data['data'] = [data['data']]
                        tmpStmp = data['timestamp']
                    else:
                        diff = self.interval / len(data['data'])
                        tmpStmp = [
                            data['timestamp'] - timedelta(seconds=i*diff) \
                            for i in range(len(data['data'][0]))
                        ][::-1]
                    tmp = pd.DataFrame(
                        zip(*data['data']+[tmpStmp]),
                        columns=self.df.columns
                    ).astype(self.datatype)
                    self.logger.info(f'received {len(tmp)} rows of data')
                    length = len(self.df)
                    if length == 0:
                        self.df = tmp
                    if length > 0:
                        self.df = pd.concat([self.df, tmp], ignore_index=True)
                    # if l + len(data['data']) > 300:
                    #     self.df = self.df[l-300:]
                    #TODO -> an dieser Stelle kann zum File geschrieben werden
            return False

class TransportFactory:
    def __init__(self, ) -> None:
        pass