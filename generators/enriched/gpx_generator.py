#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import gpxpy
import gpxpy.gpx
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class GPXGenerator(BaseGenerator):
    
    def get_format_type(self) -> str:
        return 'gpx-enriched'
    
    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        output_file = output_dir / data.get("analysis_id", "unknown") / f'enriched_track_{data.get("analysis_id", "unknown")}.gpx'
        
        try:
            gpx = gpxpy.gpx.GPX()
            
            track_points = data.get('track_points', [])
            if track_points:
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
            
            pois = data.get('pois', [])
            for i, poi in enumerate(pois):
                name = poi.get('name') or f"POI_{poi.get('type', 'unknown')}_{i+1}"
                
                waypoint = gpxpy.gpx.GPXWaypoint(
                    latitude=poi.get('lat', 0),
                    longitude=poi.get('lon', 0),
                    name=name,
                    description=f"Type: {poi.get('type', 'unknown')}, Distance: {poi.get('distance', 0):.2f} km"
                )
                gpx.waypoints.append(waypoint)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(gpx.to_xml())
            
            logger.info(f"GPX enrichi généré: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Erreur GPX enrichi: {e}")
            return None