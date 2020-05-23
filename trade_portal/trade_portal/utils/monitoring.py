import logging
import sys
from functools import wraps

import statsd
from django.conf import settings

logger = logging.getLogger(__name__)

if settings.STATSD_HOST:
    statsd.Connection.set_defaults(
        host=settings.STATSD_HOST,
        port=settings.STATSD_PORT,
        sample_rate=1,
        disabled=False
    )


def get_stack_size():
    """Get stack size for caller's frame.

    %timeit len(inspect.stack())
    8.86 ms ± 42.5 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
    %timeit get_stack_size()
    4.17 µs ± 11.5 ns per loop (mean ± std. dev. of 7 runs, 100000 loops each)
    """
    size = 2  # current frame and caller's frame always exist
    while True:
        try:
            sys._getframe(size)
            size += 1
        except ValueError:
            return size - 1  # subtract current frame


base_stack = get_stack_size() + 30


class statsd_timer():
    def __init__(self, counter_name):
        self.counter_name = counter_name

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not settings.STATSD_HOST:
                result = func(*args, **kwargs)
                return result
            scl = statsd.Timer(settings.STATSD_PREFIX)
            scl.start()
            result = None
            try:
                result = func(*args, **kwargs)
            except Exception:
                raise
            finally:
                scl.stop(self.counter_name)
            return result

        return wrapper


def statsd_gauge(name, value):
    try:
        if not isinstance(value, (float, int)):
            value = float(value)
        if not settings.STATSD_HOST:
            return
        else:
            gauge = statsd.Gauge(settings.STATSD_PREFIX)
            gauge.send(name, value)
    except Exception as e:
        logger.exception(e)


def statsd_counter(name, value):
    try:
        if not isinstance(value, (float, int)):
            value = float(value)
        if not settings.STATSD_HOST:
            return
        else:
            counter = statsd.Counter(settings.STATSD_PREFIX)
            counter.increment(name, value)
    except Exception as e:
        logger.exception(e)
