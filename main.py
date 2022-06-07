import sys
import curses
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
    while True:
        #upperwin.clear()
        try:
            inp = commandQueue.get(timeout=0.1)
            outputQueue.put(inp)
            if inp == 'close':
                conn.close()
            if inp == 'open':
                conn.open()
            if inp == 'exit':
                return          
            #upperwin.addstr(inp)
            #upperwin.addch('\n') 
        except queue.Empty:
            pass
        except curses.error:
            pass
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
    send_q = Queue()
    port = sys.argv[0] if len(sys.argv) == 2 else 'COM3'
    baud = sys.argv[1] if len(sys.argv) == 2 else 500000
    conn = Conn(port=port, baud=baud, recv=send_q)
    outputQueue = conn.getQueue()
    #conn.run()

    outputThread = threading.Thread(target=outputFunc)
    inputThread = threading.Thread(target=inputFunc)
    outputThread.start()
    inputThread.start()
    outputThread.join()
    inputThread.join()

    stdscr.keypad(False)
    curses.endwin()
    
