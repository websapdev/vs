__version__ = "0.0.0"


class Coverage:  # pragma: no cover - shim
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        return self

    def stop(self):
        return self

    def save(self):
        return self
