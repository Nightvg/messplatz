from time import sleep
from messplatz import Manager
import numpy as np


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
    frequency=1666,
    serial=True
)
a.start()
sleep(5)
a.close()