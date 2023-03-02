from messplatz import Manager
import numpy as np
from time import sleep

try:
    a = Manager(
        datatype={
            'EMG1':np.float32,
            'EMG2':np.float32,
            'ECG':np.float32,
            'BRRRRR':np.float32,
            'EDA':np.float32
        },
        name='microcontroller',
        sockport=3001,
        serial=True
    )
    a.start()
    while True:
        sleep(0.5)

except KeyboardInterrupt:
    a.close()
except Exception:
    a.close()