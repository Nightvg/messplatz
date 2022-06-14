import queue
import serial
import numpy as np
from queue import Queue
from matplotlib import pyplot as plt
from matplotlib import animation

class Conn(serial.Serial):
    def __init__(self, *args, **kwargs) -> None:
        self.__endflag = False
        self.__send = Queue()
        try:
            port = kwargs['port'] if 'port' in kwargs.keys() else args[0]
            baud = kwargs['baud'] if 'baud' in kwargs.keys() else args[1]
        except SyntaxError as e:
            self.__send.put(e)
            self.__send.put('[CONN] Coud not fit arguments, 2 needed but {} provided'.format(len(args)))
            return
        try:
            super().__init__(port=port, baudrate=baud, timeout=0.1)
            if self.is_open:
                self.close()
            self.open()
            self.__send.put('[CONN] Connection successfuly established')
        except Exception as e:
            self.__send.put(e)
            self.__send.put('[CONN] Connection error')

    def __del__(self) -> None:
        self.close()

    def close(self) -> None:
        super().close()
        self.__endflag = True

    def open(self) -> bool:
        if self.__endflag:
            self.__endflag = False
            if not self.__serial.is_open:
                self.__serial.open()
            return True
        else:
            return False

    def getQueue(self) -> Queue:
        return self.__send
                
    def read(self) -> None:
        try:
            ret = super().read(70).decode('utf-8') if not self.__endflag else ''
            if ret != '':
                ret = ret.split('\n\r')[0]
                self.__send.put('[DATA]#'+ret)
        except queue.Empty:
            pass

class Graph():
    def __init__(self, *args, **kwargs) -> None:
        try:
            self.__lim = int(np.ceil(np.sqrt(kwargs['num']))) if 'num' in kwargs.keys() else int(np.ceil(np.sqrt(args[0])))
            self.__q = kwargs['q'] if 'q' in kwargs.keys() else args[1]
            self.__data = kwargs['data'] if 'data' in kwargs.keys() else args[2]
        except Exception as e:
            self.__q.put('[GRAPH] ' + str(e))
        try:
            self.__fig, self.__axes = plt.subplots(self.__lim, self.__lim)
            self.__data = self.__data if len(self.__data) <= self.__lim**2 else self.__data[:self.__lim**2]
            self.__plot1Func = lambda *arg : arg[0].plot(np.arange(len(arg[1])), arg[1])
            self.plotAll = lambda : [self.__plot1Func(ax, a) for ax, a in zip([y for x in self.__axes for y in x], self.__data)]
            self.__animation = animation.FuncAnimation(self.__fig, self.plotAll, interval=100)
            self.show()
        except Exception as e:
            self.__q.put('[GRAPH] ' +str(e))

    def addData(self, data, num=0) -> None:
        if num > 0:
            self.__data[num].append(data)
            for x in self.__data[:num] + self.__data[num + 1:]:
                x.append(x[-1])
        else:
            data = data if len(data) == self.__lim**2 else data + [0]*(self.__lim**2 - len(data))
            self.__data = [x+[y] for x,y in zip(self.__data, data)]

    def show(self) -> None:
        plt.show()

    def getQueue(self) -> Queue:
        return self.__q

        


