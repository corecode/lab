import time
import math
import itertools

class Log:
    def __init__(self, *fields):
        self.fields = fields
        self.names = ['time'] + [f.__name__ for f in self.fields]

    def pretty_record(self, data):
        t = ''
        s = ''
        for k,v in zip(self.names, data):
            if k != 'time':
                s += ' %s=%0.5f' % (k,v)
            else:
                t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v))
        return t + s

    def run(self, interval=1.0, duration=math.inf, condition=lambda: True):
        start_time = time.time()
        gen_time = (max(0, i * interval + start_time - time.time()) for i in itertools.count(1))
        while condition() and time.time() - start_time < duration:
            now = time.time()
            yield [now] + [f() for f in self.fields]
            time.sleep(next(gen_time))
