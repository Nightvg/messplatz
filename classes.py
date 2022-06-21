import queue
import matplotlib
import serial
import numpy as np
from queue import Queue
from matplotlib import pyplot as plt
matplotlib.use('qtagg')

class Conn(serial.Serial):
    def __init__(self, *args, **kwargs) -> None:
        self.__endflag = True
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
            if not self.is_open:
                super().open()
            return True
        else:
            return False

    def getQueue(self) -> Queue:
        return self.__send
                
    def read(self) -> None:
        try:
            ret = super().read(70).decode('utf-8') if not self.__endflag else ''
            if ret != '':
                if ret[0] !='A':
                    ret = ret[ret.find('A'):] + super().read(ret.find('A') + 1).decode('utf-8')
                ret = ret.split('\n\r')[0][1:]
                self.__send.put('[DATA]#'+ret)
        except queue.Empty:
            pass

class Graph():
    def __init__(self, *args, **kwargs) -> None:
        try:
            #Necessary arguments
            self.__lim = int(np.ceil(np.sqrt(kwargs['num']))) if 'num' in kwargs.keys() else int(np.ceil(np.sqrt(args[0])))
            self.__q = kwargs['q'] if 'q' in kwargs.keys() else args[1]
            #Optional arguments
            if 'info' in kwargs.keys() or len(args) >= 3:
                self.__info = kwargs['info'] if 'info' in kwargs.keys() else args[2]
        except Exception as e:
            self.__q.put('[GRAPH] ' + str(e))
        try:
            self.__fig, self.__axes = plt.subplots(self.__lim, self.__lim)
            for x in self.__axes.reshape(self.__lim**2):
                x.set_xlim([0,50])
                x.set_ylim([-200, 1500])
                x.autoscale()
            self.__ln = [ax.plot([], lw=3, animated=True)[0] for ax in self.__axes.reshape(self.__lim**2)]
            self.__fig.canvas.draw()
            self.__bg = [self.__fig.canvas.copy_from_bbox(x.bbox) for x in self.__axes.reshape(self.__lim**2)]
            self.__rr = 4*[100*[0.0]]
            plt.show(block=False)
            #plt.pause(.1)
        except Exception as e:
            self.__q.put('[GRAPH] ' +str(e))

    def addData(self, data, num=0) -> None:
        #Update specific graph
        if num > 0:
            self.__ln[num].set_data(np.linspace(0,50., num=100), self.__rr[num])           
        #Update every graphs (including empty ones which will be filled with zeros)
        else:
            data = data if len(data) == self.__lim**2 else data + (self.__lim**2 - len(data)) * [0.0]
            i = 0
            for x, y, ax, bg in zip(self.__ln, data, self.__axes.reshape(self.__lim**2), self.__bg):
                ymin, ymax = ax.get_ylim()
                ax.set_ylim([ymin if ymin < y else y - 500, ymax if ymax > y else y + 500])
                self.__rr[i].pop(0)
                self.__rr[i].append(y)
                x.set_data(np.linspace(0,50., num=100),self.__rr[i])
                self.__fig.canvas.restore_region(bg)
                ax.draw_artist(x)
                self.__fig.canvas.blit(ax.bbox)
                i += 1
            self.__fig.canvas.flush_events()

    def getQueue(self) -> Queue:
        return self.__q

        


