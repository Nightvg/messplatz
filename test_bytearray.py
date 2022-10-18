import messplatz
import pytest

def test_instance():
    a = messplatz.ByteArray()
    assert isinstance(a, messplatz.ByteArray)
    assert isinstance(a(), messplatz.ByteArray)
    assert isinstance(a(b''), messplatz.ByteArray)
    assert isinstance(a(b'\x00\x01\x02\x03\x04\x05'), messplatz.ByteArray)

def test_objectequality():
    a = messplatz.ByteArray()
    assert a == b''
    assert a() == b''
    assert a(b'\x00\x01\x02\x03\x04\x06') == b'\x00\x01\x02\x03\x04\x06'
    assert a == b'\x00\x01\x02\x03\x04\x06'

def test_listMask():
    a = messplatz.ByteArray()
    assert messplatz.ByteArray().listMask([1,2,3]) == []
    assert messplatz.ByteArray(b'\x00\x01\x02\x03\x04\x06').listMask([1,2,3]) == [b'\x00', b'\x01\x02', b'\x03\x04\x06']
    assert messplatz.ByteArray(b'\x00').listMask([1,2,3]) == [b'\x00']
    assert messplatz.ByteArray(b'\x00').listMask([2,1,3]) == [b'\x00']
    assert a.listMask([1,2,3]) == []
    assert a(b'\x00\x01\x02\x03\x04\x06') == [b'\x00', b'\x01\x02', b'\x03\x04\x06']
    assert a(b'\x00').listMask([1,2,3]) == [b'\x00']
    assert a(b'\x00').listMask([2,1,3]) == [b'\x00']

