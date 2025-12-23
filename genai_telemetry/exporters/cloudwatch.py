"""
AWS CloudWatch Logs exporter.
"""

import atexit
import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from genai_telemetry.exporters.base import BaseExporter

logger = logging.getLogger("genai_telemetry.exporters.cloudwatch")


class CloudWatchExporter(BaseExporter):
    """Sends logs to AWS CloudWatch Logs."""
    
    def __init__(
        self,
        log_group: str = "/genai/traces",
        log_stream: str = None,
        region: str = "us-east-1",
        access_key_id: str = None,
        secret_access_key: str = None,
        batch_size: int = 10,
        flush_interval: float = 5.0
    ):
        """
        Initialize CloudWatch exporter.
        
        Args:
            log_group: CloudWatch log group name
            log_stream: CloudWatch log stream name (auto-generated if not provided)
            region: AWS region
            access_key_id: AWS access key (uses environment if not provided)
            secret_access_key: AWS secret key (uses environment if not provided)
            batch_size: Number of logs to batch before sending
            flush_interval: Seconds between automatic flushes
        """
        self.log_group = log_group
        self.log_stream = log_stream or f"genai-{datetime.now().strftime('%Y-%m-%d')}"
        self.region = region
        self.access_key_id = access_key_id or os.environ.get("AWS_ACCESS_KEY_ID")
        self.secret_access_key = secret_access_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self._batch: List[dict] = []
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None
        self._running = False
        self._sequence_token = None
        
        atexit.register(self.stop)
    
    def start(self) -> None:
        """Start the exporter and background flush thread."""
        if self._running:
            return
        self._running = True
        if self.batch_size > 1:
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._flush_thread.start()
    
    def stop(self) -> None:
        """Stop the exporter and flush remaining data."""
        self._running = False
        self.flush()
    
    def _flush_loop(self) -> None:
        """Background thread for periodic flushing."""
        while self._running:
            time.sleep(self.flush_interval)
            self.flush()
    
    def flush(self) -> None:
        """Flush any buffered logs."""
        with self._lock:
            if not self._batch:
                return
            batch = self._batch.copy()
            self._batch = []
        self._send_batch(batch)
    
    def _send_batch(self, batch: List[dict]) -> bool:
        """Send batch to CloudWatch (requires boto3)."""
        if not batch:
            return True
        
        # Try using boto3 if available
        try:
            import boto3
            client = boto3.client(
                "logs",
                region_name=self.region,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key
            )
            
            log_events = []
            for span in batch:
                log_events.append({
                    "timestamp": int(time.time() * 1000),
                    "message": json.dumps(span)
                })
            
            kwargs = {
                "logGroupName": self.log_group,
                "logStreamName": self.log_stream,
                "logEvents": log_events
            }
            
            if self._sequence_token:
                kwargs["sequenceToken"] = self._sequence_token
            
            try:
                response = client.put_log_events(**kwargs)
                self._sequence_token = response.get("nextSequenceToken")
                return True
            except client.exceptions.ResourceNotFoundException:
                # Create log group and stream
                try:
                    client.create_log_group(logGroupName=self.log_group)
                except:
                    pass
                try:
                    client.create_log_stream(logGroupName=self.log_group, logStreamName=self.log_stream)
                except:
                    pass
                response = client.put_log_events(**kwargs)
                self._sequence_token = response.get("nextSequenceToken")
                return True
                
        except ImportError:
            logger.warning("boto3 not installed. Install with: pip install boto3")
            return False
        except Exception as e:
            logger.error(f"CloudWatch Error: {e}")
            return False
    
    def export(self, span_data: Dict[str, Any]) -> bool:
        """Export a single span as a log entry."""
        if self.batch_size <= 1:
            return self._send_batch([span_data])
        
        with self._lock:
            self._batch.append(span_data)
            should_flush = len(self._batch) >= self.batch_size
        
        if should_flush:
            self.flush()
        return True
