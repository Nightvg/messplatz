from time import sleep
from messplatz import Manager
import numpy as np
import sys

TIME = sys.argv[0] if len(sys.argv) > 0 else 5
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