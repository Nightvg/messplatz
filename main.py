from time import sleep
from messplatz import Manager, init
import numpy as np
import sys

TIME = int(sys.argv[1]) if len(sys.argv) > 1 else 5
FREQ = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
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
        frequency=FREQ,
        serial=True
    )
    a.start()
    sleep(TIME)
    a.close()
except Exception as e:
    print(f'{e}')