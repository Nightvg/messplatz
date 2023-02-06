import argparse
from scipy.signal import iirdesign
import json
from requests import post
import inspect

parser = argparse.ArgumentParser(description='Return iir filter array based on input')
for var in dict(inspect.signature(iirdesign).parameters).values():
    parser.add_argument(
        f'--{var.name}',
        dest=var.name, 
        default=var.default if var.default is not inspect._empty else None
    )
test = iirdesign(**parser.parse_args())
print(test)
post('localhost/:filter', json=json.dumps(test))


