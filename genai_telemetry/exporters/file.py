"""
File exporter for writing spans to JSONL files.
"""

import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict

from genai_telemetry.exporters.base import BaseExporter

logger = logging.getLogger("genai_telemetry.exporters.file")


class FileExporter(BaseExporter):
    """Writes spans to a JSONL file."""
    
    def __init__(self, file_path: str, rotate_size_mb: int = 100):
        """
        Initialize file exporter.
        
        Args:
            file_path: Path to the output file
            rotate_size_mb: Rotate file when it exceeds this size in MB
        """
        self.file_path = file_path
        self.rotate_size_mb = rotate_size_mb
        self._lock = threading.Lock()
    
    def export(self, span_data: Dict[str, Any]) -> bool:
        """Write span to file as JSON line."""
        try:
            with self._lock:
                # Check for rotation
                if os.path.exists(self.file_path):
                    size_mb = os.path.getsize(self.file_path) / (1024 * 1024)
                    if size_mb >= self.rotate_size_mb:
                        rotated = f"{self.file_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        os.rename(self.file_path, rotated)
                
                with open(self.file_path, "a") as f:
                    f.write(json.dumps(span_data) + "\n")
            return True
        except Exception as e:
            logger.error(f"File write error: {e}")
            return False
