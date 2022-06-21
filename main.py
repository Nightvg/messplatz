import sys
import curses
import threading
from classes import *

commandQueue = Queue()
outputQueue = Queue()

stdscr = curses.initscr()
stdscr.keypad(True)
curses.curs_set(False)

upperwin = stdscr.subwin(10, 80, 0, 0)
lowerwin = stdscr.subwin(10,0)

def outputFunc():
    upperwin.scrollok(True)
    g = Graph(4, outputQueue)
    while True:
        try:
            inp = commandQueue.get(timeout=0.1)
            upperwin.addstr(str(inp))
            upperwin.addch('\n')
            if inp == 'close':
                conn.close()
            if inp == 'open':
                conn.open()
            if inp == 'exit':
                return     
            if inp.split(' ')[0] == 'write':
                conn.write(inp.split(' ')[1].encode())
        except queue.Empty:
            pass
        except curses.error as e:
            print(e)
        try:
            if conn.is_open: 
                conn.read()
        except Exception as e:
            upperwin.addstr(str(e))
            upperwin.addch('\n')
        try:
            out = outputQueue.get(timeout=0.1)
            if '[DATA]' in out:
                g.addData([float(x) for x in out.split('#')[1].split(',')])
            upperwin.addstr(str(out))
            upperwin.addch('\n')
        except queue.Empty:
            pass
            #g.addData(4*[0.0])
        except curses.error:
            print(e)
        upperwin.refresh()
        

def inputFunc():
     while True:
        global buffer
        lowerwin.addstr("->")
        command = lowerwin.getstr()

        if command:
            command = command.decode("utf-8")
            commandQueue.put(command)
            lowerwin.clear()
            lowerwin.refresh()
            if command == 'exit':
                return

if __name__ == '__main__':
    port = sys.argv[0] if len(sys.argv) == 2 else 'COM3'
    baud = sys.argv[1] if len(sys.argv) == 2 else 512000
    conn = Conn(port=port, baud=baud)
    outputQueue = conn.getQueue()

    outputThread = threading.Thread(target=outputFunc)
    inputThread = threading.Thread(target=inputFunc)
    outputThread.start()
    inputThread.start()
    outputThread.join()
    inputThread.join()

    stdscr.keypad(False)
    curses.endwin()
    
