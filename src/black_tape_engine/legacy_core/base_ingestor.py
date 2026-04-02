class BaseIngestor:
    """Base class for all ingesters."""

    def ingest(self, source):
        raise NotImplementedError("Ingest method not implemented.")
