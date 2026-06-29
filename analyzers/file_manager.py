#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Optional
import logging
import shutil

from config import MAX_GPX_SIZE_MB, GPX_DIR, AVAILABLE_TYPE_GPX_SOURCE

logger = logging.getLogger(__name__)

class FileManager:
    """Gestionnaire des fichiers pour l'analyse"""
    
    VALID_EXTENSIONS = ['.' + item['type'] for item in AVAILABLE_TYPE_GPX_SOURCE]
    
    @staticmethod
    def validate_file(file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Valide un fichier source
        
        Returns:
            (is_valid, error_message)
        """
        if not file_path.exists():
            return False, f"Fichier introuvable: {file_path}"
        
        if file_path.suffix.lower() not in FileManager.VALID_EXTENSIONS:
            return False, f"Extension non supportee: {file_path.suffix}. Supporte: {FileManager.VALID_EXTENSIONS}"
        
        size_mb = file_path.stat().st_size / (1024.0 * 1024.0)
        if size_mb > MAX_GPX_SIZE_MB:
            return False, f"Fichier trop volumineux: {size_mb:.2f} MB > {MAX_GPX_SIZE_MB} MB"
        
        return True, None
    
    @staticmethod
    def save_source_file(input_file: Path, analysis_id: str) -> Optional[Path]:
        """
        Sauvegarde le fichier source dans GPX_DIR
        
        Args:
            input_file: Chemin du fichier source
            analysis_id: ID de l'analyse
            
        Returns:
            Chemin du fichier sauvegarde ou None
        """
        try:
            gpx_analysis_dir = GPX_DIR / analysis_id
            gpx_analysis_dir.mkdir(parents=True, exist_ok=True)
            
            dest_file = gpx_analysis_dir / input_file.name
            shutil.copy2(input_file, dest_file)
            
            if dest_file.exists() and dest_file.stat().st_size == input_file.stat().st_size:
                logger.info(f"Fichier source copie: {input_file} -> {dest_file}")
                return dest_file
            
            return None
        except Exception as e:
            logger.error(f"Erreur sauvegarde fichier source: {e}")
            return None
    
    @staticmethod
    def get_file_info(file_path: Path) -> dict:
        """Retourne les informations d'un fichier"""
        return {
            'name': file_path.name,
            'size_mb': round(file_path.stat().st_size / (1024.0 * 1024.0), 2),
            'path': str(file_path),
            'extension': file_path.suffix.lower()
        }