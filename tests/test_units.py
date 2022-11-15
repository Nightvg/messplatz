from messplatz import TimeSync, CtrlFlags, ByteArray, Reader, PacketReceiver, PacketSender, PacketManager, Data, Datas, Device
from socket import socket, SOCK_STREAM, AF_INET
from datetime import datetime
import pytest
import serial
from multiprocessing import Process
from threading import Lock
import numpy as np
from sys import platform
from time import sleep

def test_ByteArray_instance():
    a = ByteArray()
    assert isinstance(a, ByteArray)

def test_ByteArray_empty_object_equality():
    a = ByteArray()
    assert a == b''

def test_ByteArray_listMask_empty():
    a = ByteArray()
    assert ByteArray().listMask([1,2,3]) == []
    assert a.listMask([1,2,3]) == []

def test_ByteArray_listMask_static():
    assert ByteArray(b'\x00\x01\x02\x03\x04\x06').listMask([1,2,3]) == [b'\x00', b'\x01\x02', b'\x03\x04\x06']
    assert ByteArray(b'\x00').listMask([1,2,3]) == [b'\x00']
    assert ByteArray(b'\x00').listMask([2,1,3]) == [b'\x00']
    
def test_ByteArray_listMask_nonstatic():
    a = ByteArray(b'\x00\x01\x02\x03\x04\x06')
    assert a.listMask([1,2,3]) == [b'\x00', b'\x01\x02', b'\x03\x04\x06']
    a = ByteArray(b'\x00')
    assert a.listMask([1,2,3]) == [b'\x00']
    assert a.listMask([2,1,3]) == [b'\x00']

def test_Data_name():
    a = Data([1,2,3,4], dtype=np.float32, name='uc')
    assert a.name == 'uc'

def test_Data_dtype():
    a = Data([1,2,3,4], dtype=np.float32, name='uc')
    assert a.dtype == np.float32

def test_Data_eq():
    a = Data([1,2,3,4], dtype=np.float32, name='uc')
    assert a == np.arange(1, 5, dtype=np.float32)

def test_Data_add():
    a = Data([1,2,3,4], dtype=np.float32, name='uc')
    assert a + 5 == np.arange(1, 6, dtype=np.float32)

def test_Data_iadd():
    a = Data([1,2,3,4], dtype=np.float32, name='uc')
    a += 5
    assert a == np.arange(1, 6, dtype=np.float32)

def test_Datas_dtypes():
    a = Datas([Data([1,2,3,4], dtype=np.int64), Data([5,6,7,8], dtype=np.int16)])
    assert a.dtypes() == [np.int64, np.int16]
    a = Datas([[1,2,3,4], np.arange(1,6, dtype=np.float16)])
    assert a.dtypes()[1] == np.float16

def test_Datas_toBytes():
    a = Datas([Data([1,2,3,4], dtype=np.int64), Data([5,6,7,8], dtype=np.int16)])
    assert a.toBytes() == np.array([1,2,3,4], dtype=np.int64).tobytes() + np.array([5,6,7,8], dtype=np.int16).tobytes() 

def test_Datas_iadd():
    a = Datas([Data([1,2,3,4], dtype=np.int64), Data([5,6,7,8], dtype=np.int16)])
    a += [5,9]
    assert a[0] == np.arange(1,6, dtype=np.int64) and a[1] == np.arange(5,10, dtype=np.int16)

def test_Datas_fromBytes():
    a = Datas([Data([1,2,3,4], dtype=np.int64), Data([5,6,7,8], dtype=np.int16)])
    assert a.fromBytes(a.toBytes()) == a
    a = a.fromBytes(10*b'\x00')
    assert a == Datas([np.array([0], dtype=np.int64), np.array([0], dtype=np.int16)])

def test_Datas_getMean():
    a = Datas([Data([1,2,3,4], dtype=np.int64), Data([5,6,7,8], dtype=np.int16)])
    assert np.array_equal(a.getMean(), [np.mean(a[0]), np.mean(a[1])])

def test_Device():
    a = Device(name='uc', d={'EMG1':np.float64})
    assert a.name == 'uc'
    assert str(a) == 'uc'
    assert isinstance(a.datas, Datas)
    a.datas += [[1,2,3,4,5]]
    assert np.arange(1,6) in a.datas
    assert a.getDict() == {'EMG1':np.float64}
    b = Device(Datas([[1,2,3,4,5], np.array([6,7,8,9,10], dtype=np.float16)]), name='t')
    assert b != a

def test_Device_pop():
    a = Device(Datas([Data([1,2,3,4], dtype=np.int64), Data([5,6,7,8], dtype=np.int16)]))
    assert a.pop() == Device(Datas([Data([4], dtype=np.int64), Data([8], dtype=np.int16)]))

def test_TimeSync():
    a = TimeSync(2020, 30)
    a.start()
    tmpDelay = []
    fl = False
    with socket(AF_INET, SOCK_STREAM) as timeSync:
        timeSync.connect(('127.0.0.1',2020))
        timeSync.send(CtrlFlags.SYNC)
        if timeSync.recv(1) == CtrlFlags.SYNC:
            for i in range(1,21):
                lT = datetime.now()
                timeSync.send(i*b'\x0c')
                if timeSync.recv(i) == i*b'\x0c':
                    tmpDelay += [(datetime.now() - lT).microseconds / 2]
            
        fl = True
    a.cancel()
    assert fl
    assert len(tmpDelay) == 20

def test_Reader_and_PacketReceiver_Message():
    tsock = socket(AF_INET, SOCK_STREAM)
    tsock.bind(('', 3001))
    p = PacketReceiver(tsock, Lock(), {})
    p.start()
    r = Reader(dev=True)
    cmpArr = [5*[np.zeros((1,)).astype(np.float32)]]
    sleep(1)
    assert p.buffer['microcontroller'].datas == cmpArr
    r.loop(5*b'1111'+b'\r\n')
    cmpArr = np.vstack((cmpArr,[5*[np.frombuffer(b'1111', np.float32)]]))
    sleep(30)
    assert np.array_equal(p.buffer['microcontroller'].datas, cmpArr)
    r.loop(200*(5*b'1111'+b'\r\n'))
    cmpArr = np.vstack((cmpArr,200*[5*[np.frombuffer(b'1111', np.float32)]]))
    sleep(2)
    assert np.array_equal(p.buffer['microcontroller'].datas, cmpArr)
    p.cancel()
    tsock.close()
    
    

@pytest.mark.skipif(platform != 'win32', reason='not a windows system')
def test_Reader_windows():
    with pytest.raises(serial.SerialException):
        a = Reader(port='COM15', baudrate=500000)
        
@pytest.mark.skipif(platform != 'linux', reason='not a linux system')
def test_Reader_linux():
    with pytest.raises(serial.SerialException):
        a = Reader(port='\ttusb3', baudrate=500000)


if __name__ == '__main__':
    a = ByteArray(b'\x01\x02')
    print(a.listMask([1,1]))
    print(a)
