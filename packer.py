import numpy as np
import socket
import pickle
import json
from websocket import create_connection
import threading
from time import sleep
from copy import deepcopy
from datetime import datetime

def packer_thread(port=3001, ws_address="127.0.0.1", ws_port=3000, dps=30):
    """
    Initializes data deploying unit. Used as virtual transport layer between view (node server) and reader.
    Needs to be started before reader and after the view server.
    Arguments:
        port        : Port to listen to, has to be the same port the reader will send data to   | int
        ws_address  : Address of websocket server (view), usually running on the same machine   | str
        ws_port     : Port of the websocket server (view), usually 3000. Unless not changend    | int
                      inside the node.js server leave this to default
        dps         : Datapackages per second                                                   | int
    Returns:
        None
    """

    bufflock = threading.Lock()
    global threadbuff
    threadbuff = {}

    node_websocket = create_connection("ws://"+ws_address+":"+str(ws_port))
    print('Starting packer..')
    packer = threading.Thread(target=packer_init, args=(bufflock, port,))
    print('Starting sender..')
    sender = threading.Thread(target=sender_init, args=(bufflock, node_websocket, dps))

    packer.start()
    #sleep(1)
    sender.start()

    packer.join()
    sender.join()

def sender_init(lock : threading.Lock, wss, dps=30):
    """
    Initializes sender unit for data deployment to wss-server. Synchronizes input data.
    Arguments:
        ws_address  : Address of websocket server (view), usually running on the same machine   | str
        ws_port     : Port of the websocket server (view), usually 3000. Unless not changend    | int
                      inside the node.js server leave this to default
    Returns:
        None
    """
    dps = 1/dps
    while True:
        lock.acquire()
        tmp_buff = deepcopy(threadbuff)
        for key in threadbuff.keys():
            if threadbuff[key].ndim > 1:
                threadbuff[key] = threadbuff[key][-1]
        lock.release()
        for device, data in tmp_buff.items():
            if data.shape[0] > 5:
                wss.send(json.dumps({'data':np.mean(data[:-1], axis=0).tolist(), 'device': device}))
                #wss.send(json.dumps({'data':data[-1].tolist(), 'device': device}))
                #print(data[:-1])
            elif data.ndim == 1:
                wss.send(json.dumps({'data': data.tolist(), 'device': device}))
        sleep(dps)

def packer_init(lock : threading.Lock, port=3001):
    """
    Initializes data buffer unit. Places data inside a buffer for boundled access from sender thread.
    Arguments:
        port        : UPD receiver port, listens for data   | int
    Returns:
        None
    """
    reader_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    reader_sock.bind(('',port))
    print('[PACKER] UDP socket ready')
    addr = {}
    while True:
        try:
            data, address = reader_sock.recvfrom(16384)
            if not address in addr.keys():
                lock.acquire()
                tmp = data.decode('utf-8')
                addr[address] = tmp[:-1]
                threadbuff[addr[address]] = np.zeros((int(tmp[-1]),)).astype(np.float32)
                lock.release()
                #reader_sock.send(b'done')
                print('[PACKER] Registered ' + tmp[:-1])
            else:
                lock.acquire()
                if pickle.loads(data) != threadbuff[addr[address]][-1]:
                    threadbuff[addr[address]] = np.vstack((threadbuff[addr[address]],pickle.loads(data))).astype(np.float32)
                lock.release()
        except Exception as e:
            print('[PACKER] ' + str(e))

#main()