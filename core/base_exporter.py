class BaseExporter:
    """Base class for all exporters."""

    def export(self, data):
        raise NotImplementedError("Export method not implemented.")
