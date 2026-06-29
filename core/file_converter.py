#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class FileConverter:
    """Convertisseur de fichiers GPS"""
    
    @staticmethod
    def convert_to_gpx(input_file: Path, output_file: Optional[Path] = None) -> Optional[Path]:
        """Convertit un fichier en GPX"""
        if not input_file.exists():
            logger.error(f"Fichier introuvable: {input_file}")
            return None
        
        if output_file is None:
            output_file = input_file.with_suffix('.gpx')
        
        logger.info(f"Conversion en GPX: {input_file} -> {output_file}")
        return output_file