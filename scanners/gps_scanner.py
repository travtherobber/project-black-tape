"""
GPS Scanner: Geospatial Signal Extraction
Heuristically identifies coordinate pairs and timestamps across heterogeneous JSON.
Optimized for Project Black-Tape Map UI.
"""

import re
import logging
from core.base_scanner import BaseScanner

logger = logging.getLogger("BLACK-TAPE.SCANNER.GPS")

class GPSScanner(BaseScanner):
    def scan(self, filename, data):
        """
        Specialized GPS Signal Extractor.
        Recursively hunts for lat/lon pairs in location, media, and vault history.
        """
        points = []
        # Pattern for lat/lon: handles negatives and decimals
        num_pattern = r"(-?\d+\.?\d*)"

        # --- 1. DEEP RECURSIVE SEARCH ---
        # Instead of hardcoded keys, we crawl the whole object for 'lat', 'lon', 'latitude', etc.
        def hunt(obj, current_ts="1970-01-01 00:00:00 UTC"):
            if isinstance(obj, dict):
                # Update timestamp if we find a date-like key nearby
                potential_ts = obj.get("Created") or obj.get("Date") or obj.get("timestamp") or obj.get("time")
                if potential_ts:
                    current_ts = f"{potential_ts} UTC" if "UTC" not in str(potential_ts) else str(potential_ts)

                # Check for direct Coordinate keys
                lat = obj.get("lat") or obj.get("latitude") or obj.get("Latitude")
                lon = obj.get("lon") or obj.get("longitude") or obj.get("Longitude")

                # Check for stringified pairs (e.g., "Location": "34.05, -118.24")
                loc_str = obj.get("Location") or obj.get("Coordinates") or obj.get("coords")

                if lat is not None and lon is not None:
                    try:
                        points.append({
                            "timestamp": current_ts,
                            "lat": float(re.search(num_pattern, str(lat)).group(1)),
                            "lon": float(re.search(num_pattern, str(lon)).group(1)),
                            "source": filename
                        })
                    except (ValueError, AttributeError): pass

                elif loc_str and isinstance(loc_str, str) and "," in loc_str:
                    parts = loc_str.split(',')
                    lat_m = re.search(num_pattern, parts[0])
                    lon_m = re.search(num_pattern, parts[1])
                    if lat_m and lon_m:
                        points.append({
                            "timestamp": current_ts,
                            "lat": float(lat_m.group(1)),
                            "lon": float(lon_m.group(1)),
                            "source": filename
                        })

                # Keep digging
                for v in obj.values():
                    hunt(v, current_ts)

            elif isinstance(obj, list):
                for item in obj:
                    hunt(item, current_ts)

        # Start the hunt
        hunt(data)

        # --- 2. LEGACY SNAPCHAT SUPPORT (Fallback) ---
        # If the recursive search missed the specific Snapchat "Location History" list format:
        if not points and "location_history" in filename.lower():
            history = data.get("Location History", [])
            for entry in history:
                if isinstance(entry, list) and len(entry) >= 2:
                    ts, coords = entry
                    parts = str(coords).split(',')
                    lat_m = re.search(num_pattern, parts[0])
                    lon_m = re.search(num_pattern, parts[1])
                    if lat_m and lon_m:
                        points.append({
                            "timestamp": f"{ts} UTC" if "UTC" not in str(ts) else str(ts),
                            "lat": float(lat_m.group(1)),
                            "lon": float(lon_m.group(1)),
                            "source": "History"
                        })

        logger.info(f"[GPS Siphon] Extracted {len(points)} geospatial markers from {filename}")
        return points
