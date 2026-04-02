import io
import json
import zipfile
from pathlib import Path


class ZipIngestor:
    """
    Handles extraction of valid chat signals from ZIP archives.
    """
    def __init__(self, max_files: int = 256, max_json_bytes: int = 32 * 1024 * 1024, max_total_bytes: int = 80 * 1024 * 1024):
        self.max_files = max_files
        self.max_json_bytes = max_json_bytes
        self.max_total_bytes = max_total_bytes

    def ingest_zip(self, file_storage):
        """
        Iterates through a ZIP file and returns a list of (filename, data) tuples
        for every JSON file found inside.
        """
        extracted_files = []

        if hasattr(file_storage, "read"):
            raw_bytes = file_storage.read()
        elif isinstance(file_storage, (str, Path)):
            raw_bytes = Path(file_storage).read_bytes()
        elif isinstance(file_storage, (bytes, bytearray)):
            raw_bytes = bytes(file_storage)
        else:
            raise TypeError(f"Unsupported zip input type: {type(file_storage)!r}")

        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
            json_infos = [info for info in z.infolist() if info.filename.endswith(".json")]
            if len(json_infos) > self.max_files:
                raise ValueError("Archive contains too many JSON files")

            total_uncompressed = 0
            for file_info in z.infolist():
                if file_info.filename.endswith('.json'):
                    if file_info.file_size > self.max_json_bytes:
                        raise ValueError(f"{file_info.filename} exceeds the per-file archive limit")
                    total_uncompressed += file_info.file_size
                    if total_uncompressed > self.max_total_bytes:
                        raise ValueError("Archive exceeds the total JSON size limit")
                    try:
                        with z.open(file_info) as f:
                            data = json.load(f)
                            extracted_files.append((file_info.filename, data))
                    except Exception as e:
                        print(f"[SYSTEM] Failed to parse {file_info.filename} in ZIP: {e}")
        
        return extracted_files
