import matplotlib
import serial
import numpy as np
from matplotlib import pyplot as plt
matplotlib.use('qtagg')
import pyqtgraph as pg

class Conn(serial.Serial):
    def __init__(self, *args, **kwargs) -> None:
        self.__endflag = True
        try:
            port = kwargs['port'] if 'port' in kwargs.keys() else args[0]
            baud = kwargs['baud'] if 'baud' in kwargs.keys() else args[1]
        except SyntaxError as e:
            print(e)
            print('[Conn] Coud not fit arguments, 2 needed but {} provided'.format(len(args)))
            return
        try:
            super().__init__(port=port, baudrate=baud, timeout=0.1)
            if self.is_open:
                self.close()
            self.open()
            print('[Conn] Connection successfuly established')
        except Exception as e:
            print('[Conn]' + str(e))

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
                
    def read(self) -> str:
        num = self.in_waiting if self.in_waiting > 70 else 70
        ret = super().read(num).decode('utf-8') if not self.__endflag else ''
        return ret[ret.find('A'):].replace('\x00','') if ret != '' else ''

#class QtGraph()

class Graph():
    def __init__(self, *args, **kwargs) -> None:
        try:
            #Necessary arguments
            self.__lim = int(np.ceil(np.sqrt(kwargs['num']))) if 'num' in kwargs.keys() else int(np.ceil(np.sqrt(args[0])))
            #Optional arguments
            if 'info' in kwargs.keys() or len(args) >= 3:
                self.__info = kwargs['info'] if 'info' in kwargs.keys() else args[2]
        except Exception as e:
            print('[Graph]' + str(e))
        try:
            self.__fig, self.__axes = plt.subplots(self.__lim, self.__lim)
            for x in self.__axes.reshape(self.__lim**2):
                x.set_xlim([0,50])
                x.set_ylim([-100, 100])
                #x.autoscale()
            self.__ln = [ax.plot([], lw=3, animated=True)[0] for ax in self.__axes.reshape(self.__lim**2)]
            self.__fig.canvas.draw()
            self.__bg = [self.__fig.canvas.copy_from_bbox(x.bbox) for x in self.__axes.reshape(self.__lim**2)]
            self.__rr = np.zeros((4,100)).tolist()
            plt.show(block=False)
            #plt.pause(.1)
        except Exception as e:
            print('[Graph]' + str(e))

    def addData(self, data, num=0) -> None:
        #Update specific graph
        if num > 0:
            self.__ln[num].set_data(np.linspace(0,50., num=100), self.__rr[num])           
        #Update every graphs (including empty ones which will be filled with zeros)
        else:
            data = data if len(data) == self.__lim**2 else data + (self.__lim**2 - len(data)) * [0.0]
            for x, y, ax, bg, rr in zip(self.__ln, data, self.__axes.reshape(self.__lim**2), self.__bg, self.__rr):                
                rr.pop(0)
                rr.append(y)
                ymin, ymax = min(rr) - 100, max(rr) + 100
                ax.set_ylim([ymin, ymax])                
                ax.yaxis.set_ticks(np.arange(ymin, ymax, abs(ymin - ymax)//4))
                x.set_data(np.linspace(0,50., num=100),rr)
                self.__fig.canvas.restore_region(bg)
                ax.draw_artist(x)
                self.__fig.canvas.blit(ax.bbox)
            self.__fig.canvas.flush_events()
    
    def AxesUpdate(ax, ):
        pass

        


