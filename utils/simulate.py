from messplatz import Manager
import numpy as np

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

except KeyboardInterrupt:
    a.close()