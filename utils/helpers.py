#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import hashlib
from typing import Any

def calculate_file_hash(file_path: Path) -> str:
    """Calcule le hash SHA-256 d'un fichier"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def format_distance(km: float) -> str:
    """Formate une distance"""
    if km < 1:
        return f"{km * 1000:.0f} m"
    return f"{km:.2f} km"

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default