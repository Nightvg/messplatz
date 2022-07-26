import sys
import argparse
import numpy as np
import serial
from numba import jit
import re
import pyqtgraph as pg
import pyqtgraph.multiprocess as mp
from tqdm import tqdm
app = pg.mkQApp('test')

#CONSTANTS
PATTERN = r'[-+]?(\d*\.\d+|\d+), [-+]?(\d*\.\d+|\d+), [-+]?(\d*\.\d+|\d+)'
PATTERN_ALT = r'[-+]?(\d*\.\d+|\d+), [-+]?(\d*\.\d+|\d+), [-+]?(\d*\.\d+|\d+), [-+]?(\d*\.\d+|\d+), [-+]?(\d*\.\d+|\d+)'

#FUNCTIONS
def update(readout) -> None:
    global rr, curves, points
    try:
        for s in readout:
            if re.fullmatch(PATTERN, s) or re.fullmatch(PATTERN_ALT, s):
                data = [float(x) for x in s.split(',')]
                for i,y in enumerate(data):          
                    if len(rr[i]) >points[i]:
                        rr[i].pop(0)
                    rr[i].append(y)
                    curves[i].setData(y=rr[i], _callSync='off')
                #print(message)              
    except Exception as e:
            print('[view] ' + str(e))

def mean_update(message):
    global rr, curves, points
    data = np.nanmean(message, axis=0)
    for i,y in enumerate(data):          
        if len(rr[i]) >points[i]:
            rr[i].pop(0)
        rr[i].append(y)
        curves[i].setData(y=rr[i], _callSync='off')

def adder(message):
    return np.array([x.split(',') + (5-len(x.split(',')))*['nan'] for x in message]).astype(float)
    

#PARSER
# parser = argparse.ArgumentParser()
# parser.add_argument('--port', '--p', required=True)
# parser.add_argument('--baud', '--b', required=True)
# parser.add_argument('--limit', '--l', required=True)
# parser.add_argument('--points', required=False)
# args = parser.parse_args()

try:
    #WINDOW
    view = mp.QtProcess()
    rpg = view._import('pyqtgraph')
    win = rpg.GraphicsLayoutWidget(show=True, title="Basic plotting examples")
    lim = 5#int(args.limit)
    points = [200,200,200,300,75]
    rpg.setConfigOptions(antialias=True)
    plots = []
    curves = []
    rr = []
    for i in range(lim):
        rr.append([])
        plots.append(win.addPlot(title='titles'))
        plots[i].enableAutoRange('xy', True)
        curves.append(plots[i].plot(pen='y'))
        #if i % 3 == 2:
        win.nextRow()
    print('[view] parameters set')        
    #READER
    conn = serial.Serial(port='COM3', baudrate=500000, timeout=0.01)
    print('[main] established connection')
    readbuffer = ''
    print('[main] socket connected')
    i = 0
    while True:
        if conn.is_open:
            readbuffer += conn.read(conn.in_waiting).decode('utf-8').replace('\x00','')
            readout = readbuffer.split('\r\n')[:-1]
            mean_update(adder(readout))
            readbuffer = readbuffer.replace('\r\n'.join(readout),'')[2:]
            print(len(readbuffer))
except Exception as e:
    print('[reader]' + str(e))
    sys.exit()