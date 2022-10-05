#Standardlib
import threading
from time import sleep
import socket
import pickle
import json
from copy import deepcopy
#Extern Packages
import numpy as np
from websocket import create_connection, WebSocket


def packer_thread(port=3001, ws_address="127.0.0.1", ws_port=3000, dps=30):
    """
    Initializes data deploying unit. Used as virtual transport layer between view (node server) and reader.
    Needs to be started before reader and after the view server.

    Arguments:
        port        : Port to listen to, has to be the same port the reader will send data to
        ws_address  : Address of websocket server (view), usually running on the same machine
        ws_port     : Port of the websocket server (view), usually 3000. Unless not changend
                      inside the node.js server leave this to default
        dps         : Datapackages per second
    Returns:
        
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

def sender_init(lock : threading.Lock, wss : WebSocket, dps=30):
    """
    Initializes sender unit for data deployment to wss-server. Synchronizes input data.

    Arguments:
        ws_address  : Address of websocket server (view), usually running on the same machine
        ws_port     : Port of the websocket server (view), usually 3000. Unless not changend
                      inside the node.js server leave this to default
    Returns:
        
    """
    dps = 1/dps
    while True:
        lock.acquire()
        tmp_buff = deepcopy(threadbuff)
        for key in threadbuff.keys():
            if threadbuff[key]['Data'].ndim > 1:
                threadbuff[key]['Data'] = threadbuff[key]['Data'][-1]
        lock.release()
        for device, dict_data in tmp_buff.items():
            res = {'data':None,'device':device}
            if not dict_data['Known']:
                res['names'] = dict_data['Keys']
                lock.acquire()
                threadbuff[device]['Known'] = True
                lock.release()
            if dict_data['Data'].ndim > 1:
                res['data'] = np.mean(dict_data['Data'][:-1], axis=0).tolist()
                #wss.send(json.dumps({'data':data[-1].tolist(), 'device': device}))
                #print(data[:-1])
            else:
                res['data'] = dict_data['Data'].tolist()
            wss.send(json.dumps(res))
        sleep(dps)

def packer_init(lock : threading.Lock, port=3001):
    """
    Initializes data buffer unit. Places data inside a buffer for boundled access from sender thread.

    Arguments:
        port        : UPD receiver port, listens for data
    Returns:
        
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
                tmp = pickle.loads(data)
                tmp_device = tmp.pop('Device')
                addr[address] = tmp_device
                threadbuff[tmp_device] = {'Data':np.zeros((len(tmp),)), 'Keys':list(tmp.keys()), 'Known':False}
                lock.release()
                #reader_sock.send(b'done')
                print('[PACKER] Registered ' + tmp_device)
            else:
                lock.acquire()
                tmp_data = pickle.loads(data)
                threadbuff[addr[address]]['Data'] = np.vstack((threadbuff[addr[address]]['Data'],tmp_data)).astype(tmp_data.dtype)
                lock.release()
        except Exception as e:
            print('[PACKER][ERROR] ' + str(e))

#main()