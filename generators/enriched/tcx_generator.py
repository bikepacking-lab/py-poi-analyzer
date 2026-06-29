#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class TCXGenerator(BaseGenerator):
    
    def get_format_type(self) -> str:
        return 'tcx-enriched'
    
    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        output_file = output_dir / data.get("analysis_id", "unknown") / f'enriched_track_{data.get("analysis_id", "unknown")}.tcx'
        
        try:
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
            
            track_points = data.get('track_points', [])
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
            
            pois = data.get('pois', [])
            if pois:
                tcx_lines.append('      <Notes>')
                tcx_lines.append('        <![CDATA[')
                tcx_lines.append('POI détectés:')
                
                for i, poi in enumerate(pois[:20], 1):
                    if isinstance(poi, dict):
                        name = poi.get('name', 'Sans nom')
                        poi_type = poi.get('type', 'unknown')
                        distance = poi.get('distance', 0)
                    else:
                        name = getattr(poi, 'name', 'Sans nom')
                        poi_type = getattr(poi, 'type', 'unknown')
                        distance = getattr(poi, 'distance', 0)
                    
                    tcx_lines.append(f'{i}. {name} ({poi_type}) - {distance:.2f} km')
                
                if len(pois) > 20:
                    tcx_lines.append(f'... et {len(pois) - 20} autres POI')
                
                tcx_lines.append('        ]]>')
                tcx_lines.append('      </Notes>')
            
            tcx_lines.append('    </Activity>')
            tcx_lines.append('  </Activities>')
            tcx_lines.append('</TrainingCenterDatabase>')
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(tcx_lines))
            
            logger.info(f"TCX enrichi généré: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Erreur TCX enrichi: {e}")
            return None