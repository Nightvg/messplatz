from click import pass_context
import messplatz
import socket
import serial
import pytest
from sys import platform

def test_reader():
    a = messplatz.Reader(dev=True)
    assert not a.is_open

    @pytest.mark.skipif(not a.is_open, reason='requires connection')
    def test_connection(a: messplatz.Reader):
        pass

def test_package_manager():
    pass

@pytest.mark.skipif(platform != 'win32', reason='not a windows system')
def test_reader_windows():
    with pytest.raises(serial.SerialException):
        a = messplatz.Reader(port='COM15', baudrate=500000)
        
@pytest.mark.skipif(platform != 'linux', reason='not a linux system')
def test_reader_linux():
    with pytest.raises(serial.SerialException):
        a = messplatz.Reader(port='\ttusb3', baudrate=500000)