from datetime import datetime
from messplatz import Manager, SerialReader, CtrlFlags
import numpy as np
from time import sleep
import pytest
import csv
import logging

@pytest.fixture(autouse=True)
def no_logs_error(caplog):
    yield
    errors = [
        record for record in caplog.get_records('call') \
        if record.levelno >= logging.ERROR
    ]
    assert not errors

def test_Manager_standard():
    TRANGE = 100
    a = Manager(
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
    a.start()
    a.reader.connectSocket()
    for _ in range(TRANGE):
        a.reader.loop(b'\x00\x10\x10\r\n\x00\x10\x20\r\n')
    a.reader.closeSocket()
    a.close()
    content = list(filter(None, list(
        csv.reader(
            open(a.dataf,'r'),
            delimiter=','
        )
    )))
    assert len(content) == 2*TRANGE + 1

def test_Manager_partlyWrongDataframes():
    TRANGE = 100
    a = Manager(
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
    a.start()
    a.reader.connectSocket()
    for i in range(TRANGE):
        a.reader.loop(b'\x00\x10\x10\r\n\x00\x10')
        a.reader.loop(b'\x20\r\n')
    a.reader.closeSocket()
    a.close()
    content = list(filter(None, list(
        csv.reader(
            open(a.dataf,'r'),
            delimiter=','
        )
    )))
    assert len(content) == 2*TRANGE + 1

def test_Manager_wrongLengthDataframes():
    TRANGE = 100
    CtrlFlags.MAXB = 2
    a = Manager(
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
    a.start()
    a.reader.connectSocket()
    for i in range(TRANGE):
        a.reader.loop(b'\x00\x10\x10\r\n')
    a.reader.closeSocket()
    a.close()
    content = list(filter(None, list(
        csv.reader(
            open(a.dataf,'r'),
            delimiter=','
        )
    )))
    assert len(content) == TRANGE + 1

def test_Manager_realconnection():
    CtrlFlags.MAXB = 2**16
    TIME = 10
    ACC = 0.15
    a = Manager(
        datatype={
            'EMG1':np.float32,
            'EMG2':np.float32,
            'ECG':np.float32,
            'BR':np.float32,
            'EDA':np.float32
        },
        name='microcontroller',
        sockport=3001,
        serial=True
    )
    if a.reader is None:
        pytest.skip('Module either not connected or not working')
    a.start()
    logging.info(f'Starting Test at: {datetime.now()}')
    sleep(TIME)
    logging.info(f'Ending Test at: {datetime.now()}')
    a.close()
    sleep(1)
    content = list(filter(None, list(
        csv.reader(
            open(a.dataf,'r'),
            delimiter=','
        )
    )))
    assert (2000*TIME+1)*(1-ACC) <= len(content) <= (2000*TIME + 1)*(1+ACC)


if __name__ == '__main__':
    a = Manager(
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
