"""
Data Ingestion Constructs for DevSecOps Platform.

This module provides comprehensive data ingestion constructs for various
data sources and ingestion patterns including batch, streaming, and real-time.
"""

from .raw_data_ingestion import RawDataIngestionConstruct, RawDataIngestionProps
from .streaming_ingestion import StreamingIngestionConstruct, StreamingIngestionProps
from .database_ingestion import DatabaseIngestionConstruct, DatabaseIngestionProps
from .api_ingestion import ApiIngestionConstruct, ApiIngestionProps
from .file_ingestion import FileIngestionConstruct, FileIngestionProps
from .batch_ingestion import BatchIngestionConstruct, BatchIngestionProps
from .realtime_ingestion import RealtimeIngestionConstruct, RealtimeIngestionProps

__all__ = [
    # Constructs
    "RawDataIngestionConstruct",
    "StreamingIngestionConstruct",
    "DatabaseIngestionConstruct",
    "ApiIngestionConstruct",
    "FileIngestionConstruct",
    "BatchIngestionConstruct",
    "RealtimeIngestionConstruct",

    # Props
    "RawDataIngestionProps",
    "StreamingIngestionProps",
    "DatabaseIngestionProps",
    "ApiIngestionProps",
    "FileIngestionProps",
    "BatchIngestionProps",
    "RealtimeIngestionProps",
]
