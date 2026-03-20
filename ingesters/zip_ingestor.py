import zipfile
import json
import io

class ZipIngestor:
    """
    Handles extraction of valid chat signals from ZIP archives.
    """
    def ingest_zip(self, file_storage):
        """
        Iterates through a ZIP file and returns a list of (filename, data) tuples
        for every JSON file found inside.
        """
        extracted_files = []
        
        # Open the zip from memory
        with zipfile.ZipFile(io.BytesIO(file_storage.read())) as z:
            for file_info in z.infolist():
                if file_info.filename.endswith('.json'):
                    try:
                        with z.open(file_info) as f:
                            data = json.load(f)
                            extracted_files.append((file_info.filename, data))
                    except Exception as e:
                        print(f"[SYSTEM] Failed to parse {file_info.filename} in ZIP: {e}")
        
        return extracted_files
