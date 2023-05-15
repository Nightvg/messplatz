from datetime import datetime, date
from messplatz import Manager, init, getLogPath
import numpy as np
import re
from time import sleep
import pytest
import csv
import logging

@pytest.fixture(autouse=True)
def no_logs_error():
    yield
    errors = re.findall(
        r'(ERROR)|(WARNING)|(CRITICAL)',
        open(f'{getLogPath()}{date.today()}.log','r').read()
    )
    assert len(errors) == 0

def test_Manager_standard():
    init()
    TRANGE = 100
    a = Manager(
        datatype={
            'EMG1':np.float16,
            'ECG':np.int8
        },
        name='micro',
        dev=True
    )
    assert a.dev
    a.start()
    for _ in range(TRANGE):
        a.reader.loop(b'\x00\x10\x10\r\n\x00\x10\x20\r\n')
    a.close()
    content = list(filter(None, list(
        csv.reader(
            open(a.dataf,'r'),
            delimiter=','
        )
    )))
    assert len(content) == 2*TRANGE + 1

def test_Manager_partlyWrongDataframes():
    init()
    TRANGE = 100
    a = Manager(
        datatype={
            'EMG1':np.float16,
            'ECG':np.int8
        },
        name='micro',
        dev=True
    )
    assert a.dev
    a.start()
    for _ in range(TRANGE):
        a.reader.loop(b'\x00\x10\x10\r\n\x00\x10')
        a.reader.loop(b'\x20\r\n')
    a.close()
    content = list(filter(None, list(
        csv.reader(
            open(a.dataf,'r'),
            delimiter=','
        )
    )))
    assert len(content) == 2*TRANGE + 1

def test_Manager_realconnection():
    init()
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
        name='microcontroller'
    )
    if not a.reader._connectFlag:
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


