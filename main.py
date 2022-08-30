from bytereader import *
from packer import *
from multiprocessing import Process

if __name__ == "__main__":
    packer = Process(target=packer_init, args=())
    reader = Process(target=reader_init, args=())

    packer.start()
    reader.start()

    packer.join()
    reader.join()