from messplatz import PacketManager, SerialReader
import numpy as np
from time import sleep
import pytest

def test_PacketManager():
    TRANGE = 100
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
    a.close()
    assert len(a._writerThread.df) == 2*TRANGE

def test_PacketManager_realconnection():
    TIME = 5
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
    if a.dev:
        pytest.skip('Module either not connected or not working')
    a.start()
    sleep(TIME)
    a.close()
    assert not any(
        (
            a._serverThread.is_alive(), 
            a._writerThread.is_alive(),
            a.reader.timer.is_alive()
        )
    )
    assert len(a._writerThread.df) == a.reader._ROWS


if __name__ == '__main__':
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
    sleep(10)
    a.close()
