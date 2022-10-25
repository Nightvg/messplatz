from messplatz import ByteArray
import pytest

def test_instance():
    a = ByteArray()
    assert isinstance(a, ByteArray)

def test_empty_object_equality():
    a = ByteArray()
    assert a == b''

def test_listMask_empty():
    a = ByteArray()
    assert ByteArray().listMask([1,2,3]) == []
    assert a.listMask([1,2,3]) == []

def test_listMask_static():
    assert ByteArray(b'\x00\x01\x02\x03\x04\x06').listMask([1,2,3]) == [b'\x00', b'\x01\x02', b'\x03\x04\x06']
    assert ByteArray(b'\x00').listMask([1,2,3]) == [b'\x00']
    assert ByteArray(b'\x00').listMask([2,1,3]) == [b'\x00']
    
def test_listMask_nonstatic():
    a = ByteArray(b'\x00\x01\x02\x03\x04\x06')
    assert a.listMask([1,2,3]) == [b'\x00', b'\x01\x02', b'\x03\x04\x06']
    a = ByteArray(b'\x00')
    assert a.listMask([1,2,3]) == [b'\x00']
    assert a.listMask([2,1,3]) == [b'\x00']

if __name__ == '__main__':
    a = ByteArray(b'\x01\x02')
    print(a.listMask([1,1]))
    print(a)
