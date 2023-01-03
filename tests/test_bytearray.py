from messplatz import ByteArray
import logging

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
    assert ByteArray(b'\x00\x01\x02\x03\x04\x06').listMask([1,2,3]) == [
            b'\x00', b'\x01\x02', b'\x03\x04\x06'
    ]
    assert ByteArray(b'\x00').listMask([1,2,3]) == [b'\x00']
    assert ByteArray(b'\x00').listMask([2,1,3]) == [b'\x00']
    
def test_ByteArray_listMask_nonstatic():
    a = ByteArray(b'\x00\x01\x02\x03\x04\x06')
    assert a.listMask([1,2,3]) == [b'\x00', b'\x01\x02', b'\x03\x04\x06']
    a = ByteArray(b'\x00')
    assert a.listMask([1,2,3]) == [b'\x00']
    assert a.listMask([2,1,3]) == [b'\x00']

def initLog():
    # create logger with 'spam_application'
    logger = logging.getLogger('messplatz')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler('main.log')
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

if __name__ == '__main__':
    a = ByteArray(100*b'\x01\x02')
    print(a.listMask([1,1]))
    print(a)