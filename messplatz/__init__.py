from copy import deepcopy
from datetime import datetime, date, timedelta
from queue import Queue #maybe obsolete
from threading import Thread, Timer, Event
from typing import Any, Callable
import logging
import requests #maybe obsolete
import os

import pandas as pd
import numpy as np
from serial import Serial
import serial.tools.list_ports as list_ports

coredir = os.path.expanduser('~')
if not os.path.exists(os.path.join(coredir,'messplatz_data\\')):
    os.mkdir(os.path.join(coredir,'messplatz_data\\'))
logpath = os.path.join(coredir,'messplatz_data\\logs\\')
datapath = os.path.join(coredir,'messplatz_data\\data\\')
if not os.path.exists(logpath):
    os.mkdir(logpath)
    # logfile = open(f'{logpath}{date.today()}.log', 'w')
    # logfile.close()
if not os.path.exists(datapath):
    os.mkdir(datapath)
logging.basicConfig(
    filename=f'{logpath}{date.today()}.log',
    filemode="a",
    format='%(asctime)s [%(levelname)s] %(message)s (%(name)s:%(lineno)s)',
    datefmt="%y-%m-%d"
)
module_logger = logging.getLogger('main.messplatz')

class CtrlFlags():
    CHNG = b'3'
    STRT = b'2'
    STOP = b'1'
    PING = b'0'
    MAXB = 8192 # 2**13

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

class Reader(Serial):    
    def __init__(
            self, 
            events: dict[str: Event],
            q: Queue,
            baudrate=500000, 
            dps=30, 
            datatype:dict={
                'EMG1':np.float32,
                'EMG2':np.float32,
                'ECG':np.float32,
                'BR':np.float32,
                'EDA':np.float32
            },
            frequency=1666,
            **kwargs
        ):
        """
        Initialize the serial reader.

        Arguments:
            events      :
            q           :
            baudrate    : datatransferrate in signes per second, usually bits
            dps         : dataframes per second
            datatype    : list of types of inputdata, has to be the same type thoughout
                          the set of inputs
            frequency   : frequency of the µC in Hz
        """
        self._connectFlag = False
        if 'dev' not in kwargs:
            #see microcontroller for baudrate, port could change on differnt devices
            for comport in list_ports.comports():
                try:
                    super().__init__(
                        self, 
                        port=comport.device,
                        baudrate=baudrate,
                        timeout=0.1
                    ) 
                    self.write(CtrlFlags.PING)
                    if self.read(2) == b'OK':
                        self._connectFlag = True
                        break
                except Exception as e:
                    self.logger.error(f'{e}')
            #enlarge input buffer
            if self._connectFlag:
                self.set_buffer_size(rx_size=1024*(2**4), tx_size=1024) 
                self.reset_input_buffer()
        else:
            super().__init__()
        self.timer = None
        self.dev = 'dev' in kwargs and kwargs['dev']
        self.MAX_ATTEMPS = 5
        self._ATTEMPTS = 0
        self.events = events
        self.q = q
        self.logger = logging.getLogger('messplatz.Reader')
        self.interval = 1/dps
        self.datatype = datatype  
        #number of bytes to read
        self.BUFFBYTES = [np.dtype(x).itemsize for x in self.datatype.values()]
        sumbuffbytes = sum(self.BUFFBYTES)
        #constant value for incorrect read
        #initialize readbuffer as byte type due to byte reading from pyserial
        self._READBUFFER = b''
        self.WRONGREAD = sumbuffbytes*b'\x00'
        #Flags and anonymous methods
        self._LCORR = lambda x : x if len(x) == sumbuffbytes else self.WRONGREAD
        self._ROWS = 0
        self._FRMS = int(1/frequency * 1e6)
        self._timeLast = None
    def loop(self, data=b'') -> None:
        def _decodeAndSend(byteString: bytes):
            elems = ByteArray(byteString).listMask(self.BUFFBYTES)
            if len(elems) > 1:
                elems = zip(*elems)
                res = [
                    np.frombuffer(b''.join(d), dtype).tolist() \
                    for d,dtype in zip(elems,self.datatype.values())
                ]
            else:
                res= [
                    np.frombuffer(d, dtype).tolist() \
                    for d,dtype in zip(elems[0],self.datatype.values())
                ]
            Thread(
                target=_asyncSend,
                kwargs={
                    'device':'microcontroller',
                    'names':list(self.datatype.keys())[:-1],
                    'ip':'127.0.0.1',
                    'datas':res,
                    'method': requests.post
                }
            ).start()
            return res
        try:
            stamplist = []            
            self._READBUFFER += self.read_all() if not self.dev else data
            if len(self._READBUFFER) == 0:
                return
            if self._timeLast is None:
                self._timeLast = datetime.now()
            splList = self._READBUFFER.split(b'\r\n')
            vals = [
                self._LCORR(dFrame) \
                for dFrame in splList[:-1]
            ] if len(splList) > 1 else [self._LCORR(splList[0])]
            stamplist = [
                np.float64(
                    (self._timeLast + timedelta(microseconds=x)).timestamp()
                )\
                for x in range(0,len(vals)*self._FRMS,self._FRMS)
            ]
            self._timeLast += timedelta(microseconds=len(vals)*self._FRMS)
            if len(self._READBUFFER) > len(self.WRONGREAD) + 2:
                self._READBUFFER = self._READBUFFER[
                    self._READBUFFER.rindex(b'\r\n')+2:
                ] 
            else:
                self._READBUFFER = b''
            self._ROWS = self._ROWS + len(vals)
            self.logger.info(
                f'sent {len(vals)} rows of data'
            )
            self.q.put({'values':_decodeAndSend(b''.join(vals)),'timestamp':stamplist})
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
        self.timer = RepeatTimer(self.interval, self.loop)
        if not self.dev:
            self.write(CtrlFlags.STRT)
        self.timer.start()

    def stop(self):
        self.logger.info('stopping connection...')
        if not self.dev:
            self.write(CtrlFlags.STOP) 
        self.events['endSend'].set()
        self.logger.info(f'Totally send: {self._ROWS}')
        self.events['endWork'].wait(timeout=None)
        if self.timer is not None:
            self.timer.cancel()

class Manager():
    def __init__(
            self,
            datatype:dict[str,Any],
            name: str,
            **kwargs
        ) -> None:      
        '''
        Initialization method. Handles traffic from the measurement unit by subdividing
        the tasks: 
            - threaded syncronous saving to file
            - threaded syncronous timed reading from 

        necessary arguments:
            datatype    : dictionary of name(s) and datatype(s) of the reader inputs
            name        : name of the device
        optional arguments:
            ip          : neccessary if receiving part is not on the local machine
            sockport    : internal port for data transmission, default 3001
        additional arguments:
            serial      : reader type serial, bool
            tablet      : reader type tablet, bool
            baudrate    : serial baudrate, default 500000
            dps         : dataframes per second, default 60
        '''
        self.logger = logging.getLogger('messplatz.PacketManager')
        self.dev = 'dev' in kwargs and kwargs['dev']
        self.dataf = ''
        self.ip = kwargs['ip'] if 'ip' in kwargs else 'localhost'
        self.datatype = datatype
        self.device = name
        self.events = {'endSend':Event(), 'endWork':Event()}
        self.port = kwargs['sockport'] if 'sockport' in kwargs else 3001
        self.q = Queue()
        self.reader = Reader(
            **{
                **kwargs,
                'events': self.events,
                'datatype': deepcopy(datatype),
                'q': self.q
            }
        )
        self.datatype['timestamp'] = np.float64
        self.BUFFBYTES = [np.dtype(x).itemsize for x in self.datatype.values()]
        self.df = pd.DataFrame(
            np.empty(
                0, dtype=[(key, np.dtype(value)) for key, value in datatype.items()]
            )
        )
        self._ThreadList = []

    def close(self) -> None:
        '''
        Blocking stop method. 
        '''
        self.reader.stop()
        for t in self._ThreadList:
            if t is not None and t.is_alive():
                t.join()

    def start(self) -> None:
        self.dataf = f'{datapath}{datetime.now().strftime("%y-%m-%d_%H-%M-%S")}.csv'
        self._ThreadList += [
            self.Write(**self.__dict__)
        ]     
        for t in self._ThreadList:
            t.start()

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
            while not (self.q.empty() and self.events['endSend'].is_set()):
                if not self.q.empty():
                    with open(self.dataf,'a') as file:
                        data = self.q.get()
                        timestamps = data['timestamp']
                        values = zip(*data['values'])
                        tmp = pd.DataFrame(
                            columns=self.df.columns
                        ).astype(self.datatype)
                        for ind,i in enumerate(values):
                            tmp.loc[ind] = [*i,timestamps[ind]]
                        self.logger.info(f'received {len(data)} rows of data')
                        if not init:
                            file.write(tmp.to_csv(index=False))
                            init = True
                        else:
                            file.write(tmp.to_csv(header=False, index=False))
            self.events['endWork'].set()
            return True

def _asyncSend(device:str, names:str, ip:str, datas:list, method:Callable):
    tmp_datas = datas
    try:
        method(
            f'http://{ip}/data',
            json={
                'names': names, 
                'device': device,
                'data': tmp_datas
            },
            headers={
                'connection': 'close'
            },
            stream=False,
            timeout=0.10
        )
    except requests.ConnectionError:
        return
    except Exception as e:
        logging.warning(f'{e}')
