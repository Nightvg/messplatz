import math
import requests
from time import sleep
from datetime import datetime

def sendOnce(**kwargs):
    kwargs['method'](
        f'http://{kwargs["ip"]}/data',
        json={
            'names': kwargs['names'], 
            'device': kwargs['device'],
            'data': kwargs['datas'],
            'len': len(kwargs['datas'][0])
        },
        headers={
            'connection': 'close'
        },
        stream=False,
        timeout=0.10
    )

def emulate(**kwargs):
    for i in range(1000):
        if i < 500:
            kwargs['datas'] = [[1000*math.sin(i/10)], [datetime.now().timestamp()]]
        else:
            kwargs['datas'] = [
                *(5*[[1000*math.sin(i/10)]]),
                [datetime.now().timestamp()]
            ]
            kwargs['names'] = ['EMG1','EMG2','ECG','BR','EDA','timestamp']
        sendOnce(**kwargs)
        sleep(kwargs['dps'])

if __name__ == '__main__':
    kwargs = {
        'device': 'test',
        'names': ['ECG','timestamp'],
        'datas': [],
        'method': requests.post,
        'ip': '127.0.0.1',
        'dps': 1/60
    }
    emulate(kwargs)
    



