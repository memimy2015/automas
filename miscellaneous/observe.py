import os
from cozeloop.decorator import observe as cozeloop_observe


def observe(*args, **kwargs):
    def decorator(func):
        enabled_wrapper = None

        def call(*f_args, **f_kwargs):
            nonlocal enabled_wrapper
            if os.getenv("AUTOMAS_ENABLE_OBSERVE", "0") == "1":
                if enabled_wrapper is None:
                    enabled_wrapper = cozeloop_observe(*args, **kwargs)(func)
                return enabled_wrapper(*f_args, **f_kwargs)
            return func(*f_args, **f_kwargs)

        return call

    return decorator
