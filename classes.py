from msilib.schema import Error
import queue
import serial
import threading
from queue import Queue

class Conn():
    def __init__(self, *args, **kwargs) -> None:
        self.__endflag = False
        self.__send = Queue()
        try:
            self.__port = kwargs['port'] if 'port' in kwargs.keys() else args[0]
            self.__baud = kwargs['baud'] if 'baud' in kwargs.keys() else args[1]
            self.__recv = kwargs['recv'] if 'recv' in kwargs.keys() else args[2]
        except SyntaxError as e:
            self.__send.put(e)
            self.__send.put('[CONN] Coud not fit arguments, 3 needed but {} provided'.format(len(args)))
            return
        try:
            self.__serial = serial.Serial(port=self.__port, baudrate=self.__baud)
            self.__serial.close()
            self.__serial.open()
            self.__send.put('[CONN] Connection successfuly established')
        except Exception as e:
            self.__send.put(e)
            self.__send.put('[CONN] Connection error')

    def __del__(self) -> None:
        self.close()

    def close(self) -> None:
        self.__serial.close()
        try:
            self.__thread.join()
        except:
            pass


    def open(self) -> bool:
        if self.__endflag:
            self.__endflag = False
            self.__serial.open()
            return True
        else:
            return False

    def getQueue(self) -> Queue:
        return self.__send

    def __write(self, data: bytes) -> None:
        self.__serial.write(data)
                
    def __read(self) -> bytes:
        return self.__serial.read()

    def __run(self):
        while not self.__endflag:
            try:
                r = self.__read()
                self.__send.put(r)
            except:
                pass
            try:
                get = self.__recv.get()
                if 'exit' in get.decode('utf-8'):
                    self.__endflag = True
                    self.close()
                else: 
                    self.__write(get)
            
            except queue.Empty():
                pass

    def run(self) -> threading.Thread:
        self.__send.put('[CONN] Start running..')
        self.__thread = threading.Thread(target=self.__run(), daemon=True)
        return self.__thread
        


