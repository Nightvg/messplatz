from time import sleep
from messplatz import Manager, init
import numpy as np
import sys

def simulate(time: int, **kwargs) -> None:
    '''
    Blocking simulation mode. Measurement for time in seconds.
    For keyword arguments, see Manager.
    '''
    init()
    a = Manager(
        datatype=kwargs['datatype'] if 'datatype' in kwargs else {
            'EMG1':np.float32,
            'EMG2':np.float32,
            'ECG':np.float32,
            'BR':np.float32,
            'EDA':np.float32
        },
        name='microcontroller',
        sockport=kwargs['sockport'] if 'sockport' in kwargs else 3001,
        frequency=kwargs['frequency'] if 'frequency' in kwargs else 2000,
        serial=True
    )
    a.start()
    sleep(time)
    a.close()

if __name__ == '__main__':
    simulate(
        int(sys.argv[1]) if len(sys.argv) > 1 else 5, 
        frequency=int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    ) 