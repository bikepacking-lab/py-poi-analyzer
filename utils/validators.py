#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)

class Validators:
    """Validateurs"""
    
    @staticmethod
    def validate_gpx_file(file_path: Path, max_size_mb: float = 2) -> Tuple[bool, Optional[str]]:
        if not file_path.exists():
            return False, f"Fichier introuvable: {file_path}"
        
        if file_path.suffix.lower() not in ['.gpx', '.kml', '.tcx', '.fit']:
            return False, f"Extension non supportée: {file_path.suffix}"
        
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            return False, f"Fichier trop volumineux: {size_mb:.2f} MB"
        
        return True, None
    
    @staticmethod
    def validate_poi_types(poi_types: List[str], available_types: List[str]) -> Tuple[bool, Optional[str]]:
        if not poi_types:
            return True, None
        
        invalid_types = [t for t in poi_types if t not in available_types]
        if invalid_types:
            return False, f"Types invalides: {', '.join(invalid_types)}"
        
        return True, None