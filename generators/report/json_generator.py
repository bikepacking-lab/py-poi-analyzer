#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class JSONGenerator(BaseGenerator):
    
    def get_format_type(self) -> str:
        return 'json'
    
    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        output_file = output_dir / f'analysis_report_{data.get("analysis_id", "unknown")}.json'
        
        try:
            # Structure complète du rapport
            report = {
                'metadata': {
                    'analysis_id': data.get('analysis_id'),
                    'generated': datetime.now().isoformat(),
                    'input_file': data.get('input_file'),
                    'version': '2.0'
                },
                'summary': data.get('summary', {}),
                'statistics': {
                    'total_distance_km': data.get('total_distance', 0),
                    'total_points': data.get('num_points', 0),
                    'segments': data.get('num_segments', 1),
                    'poi_types': data.get('poi_types', [])
                },
                'pois': self._format_pois(data.get('pois', [])),
                'track': {
                    'points_count': len(data.get('track_points', [])),
                    'bounds': self._get_bounds(data.get('track_points', []))
                },
                'configuration': {
                    'radii': data.get('radii', {}),
                    'intervals': data.get('intervals', {})
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Rapport JSON genere: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Erreur JSON: {e}")
            return None
    
    def _format_pois(self, pois: List) -> List[Dict]:
        """Formate TOUS les POI - AUCUNE LIMITE"""
        if not pois:
            return []
    
        formatted = []
        for poi in pois:
            formatted.append({
                'id': self._get_value(poi, 'id', ''),
                'type': self._get_value(poi, 'type', ''),
                'name': self._get_value(poi, 'name', 'Sans nom'),
                'location': {
                    'lat': self._get_float(poi, 'lat', 0.0),
                    'lon': self._get_float(poi, 'lon', 0.0),
                    'osm_type': self._get_value(poi, 'osm_type', 'node')
                },
                'distance_km': self._get_float(poi, 'distance', 0.0),
                'address': self._get_value(poi, 'address', ''),
                'phone': self._get_value(poi, 'phone', ''),
                'website': self._get_value(poi, 'website', ''),
                'opening_hours': self._get_value(poi, 'opening_hours', ''),
                'description': self._get_value(poi, 'description', ''),
                'links': {
                    'google_maps': self._get_value(poi, 'google_maps_url', ''),
                    'overpass': self._get_value(poi, 'overpass_url', '')
                },
                'tags': poi.get('tags', {}) if isinstance(poi, dict) else getattr(poi, 'tags', {})
            })
    
        logger.info(f"JSON: {len(formatted)} POI exportes")
        return formatted
    
    def _get_bounds(self, track_points: List) -> Dict:
        """Calcule les limites de la trace"""
        if not track_points:
            return {}
        
        lats = [p.get('latitude', 0) for p in track_points]
        lons = [p.get('longitude', 0) for p in track_points]
        
        return {
            'min_lat': min(lats),
            'max_lat': max(lats),
            'min_lon': min(lons),
            'max_lon': max(lons)
        }
        
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