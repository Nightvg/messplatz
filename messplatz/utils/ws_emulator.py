from websocket import create_connection
from time import sleep
import json
import math

ws = create_connection("ws://127.0.0.1:3000")
dps = 1/30
i = 0
def jss(x,names):
    return json.dumps({
    'names': names, 
    'data': len(names)*[1000*math.sin(x/10)],
    'device': 'tester'
})
while i < 1000:
    try:
        if i < 500:
            ws.send(
                jss(i,['BRR','LEE'])
            )
        if i >= 500 and i < 1000:
            ws.send(
                jss(i,['BRR','LEE','REE','MEE'])
            )
        i += 1
        sleep(dps)
    except KeyboardInterrupt:
        break
