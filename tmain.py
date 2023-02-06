from messplatz import PacketManager
import numpy as np
from time import sleep

if __name__ == '__main__':
    pM = PacketManager(datatype={'EMG1':np.float32, 'EMG2':np.float32, 'ECG':np.float32, 'BR':np.float32, 'EDA':np.float32},name='messplatz', serial=True)
    try:
        pM.start()
    except KeyboardInterrupt:
        pM.close()
    # try:
    #     pM.close()
    # except:
    #     pass