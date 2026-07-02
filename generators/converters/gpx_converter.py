#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import gpxpy
import gpxpy.gpx
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class GPXConverter(BaseGenerator):
    """Convertisseur GPX sans POI"""

    def get_format_type(self) -> str:
        return 'gpx'

    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        """Génère un GPX sans POI"""
        try:
            track_points = data.get('track_points', [])
            
            if not track_points:
                logger.warning("Aucun point de trace pour le GPX")
                return None

            gpx = gpxpy.gpx.GPX()
            gpx_track = gpxpy.gpx.GPXTrack()
            gpx.tracks.append(gpx_track)
            
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_track.segments.append(gpx_segment)
            
            for point_data in track_points:
                point = gpxpy.gpx.GPXTrackPoint(
                    point_data.get('latitude', 0),
                    point_data.get('longitude', 0),
                    elevation=point_data.get('elevation'),
                    time=point_data.get('time')
                )
                gpx_segment.points.append(point)
            
            analysis_id = data.get('analysis_id', 'unknown')
            output_file = output_dir / f"converted_track_{analysis_id}.gpx"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(gpx.to_xml())
            
            logger.info(f"GPX genere: {output_file} ({len(track_points)} points)")
            return output_file
            
        except Exception as e:
            logger.error(f"Erreur GPX: {e}")
            return None