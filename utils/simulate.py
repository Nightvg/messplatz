from messplatz import PacketManager
import numpy as np

try:
    a = PacketManager(
        datatype={
            'EMG1':np.float32,
            'EMG2':np.float32,
            'ECG':np.float32,
            'BRRRRR':np.float32,
            'EDA':np.float32
        },
        name='microcontroller',
        sockport=3001,
        serial=True,
        nows=True
    )
    a.start()

except KeyboardInterrupt:
    a.close()