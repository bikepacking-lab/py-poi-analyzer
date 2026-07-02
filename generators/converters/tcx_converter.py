#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class TCXConverter(BaseGenerator):
    """Convertisseur TCX sans POI"""

    def get_format_type(self) -> str:
        return 'tcx'

    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        """Génère un TCX sans POI"""
        try:
            track_points = data.get('track_points', [])
            
            if not track_points:
                logger.warning("Aucun point de trace pour le TCX")
                return None

            tcx_lines = []
            
            tcx_lines.append('<?xml version="1.0" encoding="UTF-8"?>')
            tcx_lines.append('<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"')
            tcx_lines.append('  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
            tcx_lines.append('  xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd">')
            tcx_lines.append('  <Activities>')
            tcx_lines.append('    <Activity Sport="Biking">')
            tcx_lines.append(f'      <Id>{datetime.now().isoformat()}</Id>')
            tcx_lines.append(f'      <Lap StartTime="{datetime.now().isoformat()}">')
            tcx_lines.append('        <Track>')
            
            for point_data in track_points[:1000]:
                tcx_lines.append('          <Trackpoint>')
                tcx_lines.append('            <Position>')
                tcx_lines.append(f'              <LatitudeDegrees>{point_data.get("latitude", 0)}</LatitudeDegrees>')
                tcx_lines.append(f'              <LongitudeDegrees>{point_data.get("longitude", 0)}</LongitudeDegrees>')
                tcx_lines.append('            </Position>')
                
                if point_data.get('elevation') is not None:
                    tcx_lines.append(f'            <AltitudeMeters>{point_data["elevation"]}</AltitudeMeters>')
                
                if point_data.get('distance') is not None:
                    tcx_lines.append(f'            <DistanceMeters>{point_data["distance"] * 1000}</DistanceMeters>')
                
                tcx_lines.append('          </Trackpoint>')
            
            tcx_lines.append('        </Track>')
            tcx_lines.append('      </Lap>')
            tcx_lines.append('    </Activity>')
            tcx_lines.append('  </Activities>')
            tcx_lines.append('</TrainingCenterDatabase>')
            
            analysis_id = data.get('analysis_id', 'unknown')
            output_file = output_dir / f"converted_track_{analysis_id}.tcx"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(tcx_lines))
            
            logger.info(f"TCX genere: {output_file} ({len(track_points)} points)")
            return output_file
            
        except Exception as e:
            logger.error(f"Erreur TCX: {e}")
            return None