#Standardlib
from bytereader import *
from packer import *
from tablet_reader import *
from time import sleep
from multiprocessing import Process
from threading import Thread

if __name__ == "__main__":
    packer = Thread(target=packer_thread, args=())
    reader = Thread(target=reader_init, args=())
    #tablet = Process(target=main_tab, args=())
    
    packer.start()
    sleep(2)
    reader.start()
    #tablet.start()

    packer.join()
    reader.join()
    #tablet.join()