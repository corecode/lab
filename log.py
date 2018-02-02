import time
import math
import itertools

class Log:
    def __init__(self, csv, *fields):
        self.csv = csv
        self.fields = fields
        self._log(['time'] + [f.__name__ for f in self.fields])

    def _log(self, data):
        self.csv.writerow(data)

    def run(self, interval, duration=math.inf, condition=lambda: True):
        start_time = time.time()
        gen_time = (max(0, i * interval + start_time - time.time()) for i in itertools.count(1))
        while condition() and time.time() - start_time < duration:
            now = time.time()
            self._log([now] + [f() for f in self.fields])
            time.sleep(next(gen_time))
