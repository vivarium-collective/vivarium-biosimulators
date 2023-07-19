import os
import json
from datetime import datetime


class ProcessLogger:
    def __init__(self, dirpath, filename='log.json'):
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)
        self.fp = os.path.join(dirpath, filename)
        self.log = {}

    def add_entry(self, entry):
        now = datetime.now().strftime('%DD_%MM_%YYYY')
        self.log[now] = [entry]

    def write_log(self, flush=False):
        with open(self.fp, 'w') as f:
            json.dump(self.log, f, indent=4)
        if flush:
            self.log.clear()

    def read_log(self, fp):
        with open(fp, 'r') as f:
            data = json.load(f)
            return data

    def flush_log(self):
        self.log.clear()
