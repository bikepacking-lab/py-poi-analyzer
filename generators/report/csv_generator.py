#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional
import csv
import logging
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class CSVGenerator(BaseGenerator):
    
    def get_format_type(self) -> str:
        return 'csv'
    
    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        output_file = output_dir / f'analysis_report_{data.get("analysis_id", "unknown")}.csv'
        
        try:
            pois = data.get('pois', [])
            
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                if not pois:
                    writer = csv.writer(f)
                    writer.writerow(['ID', 'Type', 'Nom', 'Latitude', 'Longitude', 'Distance (km)'])
                    writer.writerow(['Aucun POI trouve', '', '', '', '', ''])
                else:
                    # TOUS les POI - AUCUNE LIMITE
                    fieldnames = [
                        'ID', 'Type', 'Nom', 'Latitude', 'Longitude', 
                        'Distance (km)', 'Adresse', 'Telephone', 'Site web',
                        'Horaires', 'Description', 'Google Maps', 'Overpass'
                    ]
                    
                    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
                    writer.writeheader()
                    
                    for poi in pois:
                        # Nettoyer les valeurs pour CSV
                        row = {
                            'ID': self._get_value(poi, 'id', ''),
                            'Type': self._get_value(poi, 'type', ''),
                            'Nom': self._get_value(poi, 'name', 'Sans nom'),
                            'Latitude': self._get_float(poi, 'lat', 0.0),
                            'Longitude': self._get_float(poi, 'lon', 0.0),
                            'Distance (km)': self._get_float(poi, 'distance', 0.0),
                            'Adresse': self._get_value(poi, 'address', ''),
                            'Telephone': self._get_value(poi, 'phone', ''),
                            'Site web': self._get_value(poi, 'website', ''),
                            'Horaires': self._get_value(poi, 'opening_hours', ''),
                            'Description': self._get_value(poi, 'description', ''),
                            'Google Maps': self._get_value(poi, 'google_maps_url', ''),
                            'Overpass': self._get_value(poi, 'overpass_url', '')
                        }
                        writer.writerow(row)
                    
                    logger.info(f"CSV: {len(pois)} POI exportes")
            
            logger.info(f"Rapport CSV genere: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Erreur CSV: {e}")
            return None
    
    def _get_value(self, obj: Any, key: str, default: str = '') -> str:
        if obj is None:
            return default
        if isinstance(obj, dict):
            val = obj.get(key, default)
            return str(val) if val is not None else default
        if hasattr(obj, key):
            val = getattr(obj, key, default)
            return str(val) if val is not None else default
        return default
    
    def _get_float(self, obj: Any, key: str, default: float = 0.0) -> float:
        if obj is None:
            return default
        try:
            if isinstance(obj, dict):
                val = obj.get(key, default)
            elif hasattr(obj, key):
                val = getattr(obj, key, default)
            else:
                return default
            if val is None:
                return default
            return float(val)
        except (ValueError, TypeError):
            return default