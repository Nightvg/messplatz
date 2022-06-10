import sys
import curses
from classes import *

commandQueue = Queue()
outputQueue = Queue()
send_q = Queue()

stdscr = curses.initscr()
stdscr.keypad(True)
curses.curs_set(False)

upperwin = stdscr.subwin(10, 80, 0, 0)
lowerwin = stdscr.subwin(10,0)

def outputFunc():
    upperwin.scrollok(True)
    while True:
        try:
            inp = commandQueue.get(timeout=0.1)
            outputQueue.put(inp)
            if inp == 'close':
                conn.close()
            if inp == 'open':
                conn.open()
            if inp == 'exit':
                return     
            if inp.split(' ')[0] == 'write':
                send_q.put(inp.split(' ')[1].encode())
        except queue.Empty:
            pass
        except curses.error as e:
            outputQueue.put(e)
        try:
            out = outputQueue.get(timeout=0.1)
            upperwin.addstr(str(out))
            upperwin.addch('\n')
        except queue.Empty:
            pass
        except curses.error:
            pass
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
    baud = sys.argv[1] if len(sys.argv) == 2 else 500000
    conn = Conn(port=port, baud=baud, recv=send_q)
    outputQueue = conn.getQueue()
    t = conn.run()

    outputThread = threading.Thread(target=outputFunc)
    inputThread = threading.Thread(target=inputFunc)
    outputThread.start()
    inputThread.start()
    outputThread.join()
    inputThread.join()
    t.join()

    stdscr.keypad(False)
    curses.endwin()
    
