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
            'data': kwargs['datas']
        },
        headers={
            'connection': 'close'
        },
        stream=False,
        timeout=0.10
    )

if __name__ == '__main__':
    kwargs = {
        'device': 'test',
        'names': ['ECG','timestamp'],
        'datas': [],
        'method': requests.post,
        'ip': '127.0.0.1'
    }
    dps = 1/60
    for i in range(1000):
        if i < 500:
            kwargs['datas'] = [1000*math.sin(i/10), datetime.now().timestamp()]
        else:
            kwargs['datas'] = 2*[1000*math.sin(i/10)] + [datetime.now().timestamp()]
            kwargs['names'] = ['ECG','EMG1','timestamp']
        sendOnce(**kwargs)
        sleep(dps)



