import json
from black_tape_engine.legacy_core.base_exporter import BaseExporter

class JSONExporter(BaseExporter):
    def export(self, data, filename="output.json"):
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        return filename
