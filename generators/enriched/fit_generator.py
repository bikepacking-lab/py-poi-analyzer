#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional
import json
import logging
from datetime import datetime
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class FITGenerator(BaseGenerator):
    
    def get_format_type(self) -> str:
        return 'fit-data'
    
    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        output_file = output_dir / data.get("analysis_id", "unknown") / f'fit_data_{data.get("analysis_id", "unknown")}.json'
        
        try:
            fit_data = {
                'metadata': {
                    'version': '1.0',
                    'generated': datetime.now().isoformat(),
                    'analysis_id': data.get('analysis_id'),
                    'total_distance_km': data.get('total_distance', 0)
                },
                'track': {
                    'points': [
                        {
                            'latitude': p.get('latitude', 0),
                            'longitude': p.get('longitude', 0),
                            'elevation': p.get('elevation', 0),
                            'distance': p.get('distance', 0)
                        }
                        for p in data.get('track_points', [])[:1000]
                    ]
                },
                'pois': [
                    {
                        'id': poi.get('id'),
                        'type': poi.get('type'),
                        'latitude': poi.get('lat', 0),
                        'longitude': poi.get('lon', 0),
                        'name': poi.get('name', ''),
                        'distance_km': poi.get('distance', 0)
                    }
                    for poi in data.get('pois', [])
                ],
                'statistics': {
                    'total_distance_km': data.get('total_distance', 0),
                    'num_points': len(data.get('track_points', [])),
                    'num_pois': len(data.get('pois', []))
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(fit_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Données FIT générées: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Erreur FIT: {e}")
            return None