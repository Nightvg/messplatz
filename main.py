from time import sleep
from messplatz import Manager, init
import numpy as np
import sys

TIME = int(sys.argv[1]) if len(sys.argv) > 1 else 5
try:
    init()
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
        frequency=2000,
        serial=True
    )
    a.start()
    sleep(TIME)
    a.close()
except Exception as e:
    print(f'{e}')