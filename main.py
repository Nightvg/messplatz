#Standardlib
from bytereader import *
from packer import *
from tablet_reader import *
from time import sleep
from multiprocessing import Process

if __name__ == "__main__":
    packer = Process(target=packer_thread, args=())
    reader = Process(target=reader_init, args=())
    #tablet = Process(target=main_tab, args=())
    
    packer.start()
    sleep(2)
    reader.start()
    #tablet.start()

    packer.join()
    reader.join()
    #tablet.join()