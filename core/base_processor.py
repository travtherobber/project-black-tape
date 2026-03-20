class BaseProcessor:
    """Base class for all processors."""

    def process(self, data):
        raise NotImplementedError("Process method not implemented.")
