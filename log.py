import time
import math
import itertools

def log(*fields, interval=1.0, duration=math.inf, condition=lambda: True):
    names = ['time'] + [f.__name__ for f in fields]
    yield names

    start_time = time.time()
    gen_time = (max(0, i * interval + start_time - time.time()) for i in itertools.count(1))
    while condition() and time.time() - start_time < duration:
        now = time.time()
        yield [now] + [f() for f in fields]
        time.sleep(next(gen_time))
