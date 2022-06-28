from multiprocessing import Process
from threading import Thread
import sys
import socket
import multiprocessing as mp
from classes import *

def view():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(('', 2000))
    g = Graph(4)
    while True:
        try:
            message = server.recv(4096).decode('utf-8')
            g.addData([float(x) for x in message[1:].split(',')])
            if 'exit' in message:
                return
            print(message)
        except Exception as e:
            print('[view] ' + str(e))

def reader(print_address, port, baud):
    try:
        conn = Conn(port=port, baud=baud)
        #print_address = ('127.0.0.1', 2000)   
        print_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except Exception as e:
        print(e)
    while True:
        try:
            if conn.is_open:
                for s in conn.read().split('\n\r'):
                    if s != '':
                        print_socket.sendto(s.encode('utf-8'), print_address)
        except Exception as e:
            print('[inputhandler-map]' + str(e))

if __name__ == '__main__':
    port = sys.argv[0] if len(sys.argv) == 2 else 'COM3'
    baud = sys.argv[1] if len(sys.argv) == 2 else 500000

    inp = Process(target=reader, args=(('127.0.0.1', 2000), port, baud))
    outp = Process(target=view)

    inp.start()
    outp.start()
    inp.join()
    outp.join()
