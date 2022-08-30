import numpy as np
import socket
import pickle
import json
from websocket import create_connection

def packer_init(port=3001, ws_address="127.0.0.1", ws_port=3000):
    """
    Initializes data deploying unit. Used as virtual transport layer between view (node server) and reader.
    Needs to be started before reader and after the view server.
    Arguments:
        port        : Port to listen to, has to be the same port the reader will send data to   | int
        ws_address  : Address of websocket server (view), usually running on the same machine   | str
        ws_port     : Port of the websocket server (view), usually 3000. Unless not changend    | int
                      inside the node.js server leave this to default
    Returns:
        None
    """
    reader_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    node_websocket = create_connection("ws://"+ws_address+":"+str(ws_port))
    reader_sock.bind(('',port))
    print('Socket up')
    while True:
        try:
            data, address = reader_sock.recvfrom(16384)
            if node_websocket.connected:
                tmp_buff = pickle.loads(data)
                res_data = np.mean(tmp_buff, axis=0)
                node_websocket.send(json.dumps({'data':(res_data.T).tolist()}))
            else:
                node_websocket.connect("ws://"+ws_address+":"+str(ws_port))
        except:
            continue

#packer_init()