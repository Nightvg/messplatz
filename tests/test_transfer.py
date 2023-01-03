from messplatz import PacketManager, SerialReader
import numpy as np
from time import sleep

def test_PacketManager():
    TRANGE = 2
    a = PacketManager(
        datatype={
            'EMG1':np.float16,
            'ECG':np.int8
        },
        name='micro',
        sockport=3001,
        dev=True,
        serial=True
    )
    assert type(a.reader) == SerialReader
    assert a.dev
    a._serverThread.start()
    a._writerThread.start()
    a.reader.connectSocket()
    for i in range(TRANGE):
        a.reader.loop(b'\x00\x10\x10\r\n\x00\x10\x20\r\n')
    a.reader.closeSocket()
    assert len(a._writerThread.df) == 2*TRANGE

def test_PacketManager_realconnection():
    a = PacketManager(
        datatype={
            'EMG1':np.float32,
            'EMG2':np.float32,
            'ECG':np.float32,
            'BRRRRR':np.float32,
            'EDA':np.float32
        },
        name='microcontroller',
        sockport=3001,
        serial=True
    )
    a.start()
    sleep(1)
    a.close()
    assert len(a._writerThread.df) == a.reader._ROWS
    assert not any(
        (
            a._serverThread.is_alive(), 
            a._writerThread.is_alive(),
            a.reader.timer.is_alive()
        )
    )

if __name__ == '__main__':
    test_PacketManager()
