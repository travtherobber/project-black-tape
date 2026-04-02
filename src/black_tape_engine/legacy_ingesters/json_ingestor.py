import json
import logging

logger = logging.getLogger("BLACK-TAPE.JSON-INGESTOR")

class JSONIngestor:
    def ingest_file(self, file_handle):
        """
        Robust Load Protocol.
        Handles standard JSON, corrupted headers, and JSONL formats.
        """
        try:
            # Ensure we are at the start of the stream
            if hasattr(file_handle, 'seek'):
                file_handle.seek(0)

            # Read raw content to check for empty files
            content = file_handle.read()
            if not content:
                logger.warning("Empty signal detected. Ingestion aborted.")
                return {}

            # Attempt Standard Load
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Fallback: Is it a JSONL (Line-delimited) file?
                logger.info("Standard parse failed. Attempting JSONL recovery...")
                lines = content.decode('utf-8', errors='ignore').splitlines()
                recovered = [json.loads(l) for l in lines if l.strip()]
                return {"recovered_data": recovered} if recovered else {}

        except Exception as e:
            logger.error(f"Critical Ingestion Failure: {str(e)}")
            return {}
