#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class KMLGenerator(BaseGenerator):
    
    def get_format_type(self) -> str:
        return 'kml-enriched'
    
    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        """Génère un fichier KML enrichi à partir des données fournies"""
        
        output_file = output_dir / f'enriched_track_{data.get("analysis_id", "unknown")}.kml'
        
        try:
            kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
            document = ET.SubElement(kml, 'Document')
            
            name = ET.SubElement(document, 'name')
            name.text = 'Trace GPS enrichie'
            
            style = ET.SubElement(document, 'Style', id='trackStyle')
            line_style = ET.SubElement(style, 'LineStyle')
            color = ET.SubElement(line_style, 'color')
            color.text = 'ff0000ff'
            width = ET.SubElement(line_style, 'width')
            width.text = '4'
            
            track_points = data.get('track_points', [])
            if track_points:
                placemark = ET.SubElement(document, 'Placemark')
                style_url = ET.SubElement(placemark, 'styleUrl')
                style_url.text = '#trackStyle'
                
                line_string = ET.SubElement(placemark, 'LineString')
                alt_mode = ET.SubElement(line_string, 'altitudeMode')
                alt_mode.text = 'clampToGround'
                
                coords = ET.SubElement(line_string, 'coordinates')
                coords.text = ' '.join([
                    f"{p.get('longitude', 0)},{p.get('latitude', 0)},0"
                    for p in track_points
                ])
            
            for i, poi in enumerate(data.get('pois', [])):
                poi_placemark = ET.SubElement(document, 'Placemark')
                
                poi_name = ET.SubElement(poi_placemark, 'name')
                poi_name.text = poi.get('name', f'POI_{i+1}')
                
                description = ET.SubElement(poi_placemark, 'description')
                description.text = f"Type: {poi.get('type', 'unknown')}, Distance: {poi.get('distance', 0):.2f} km"
                
                point = ET.SubElement(poi_placemark, 'Point')
                coords_elem = ET.SubElement(point, 'coordinates')
                coords_elem.text = f"{poi.get('lon', 0)},{poi.get('lat', 0)},0"
            
            xml_str = minidom.parseString(ET.tostring(kml)).toprettyxml(indent="  ")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_str)
            
            logger.info(f"KML enrichi généré: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Erreur KML enrichi: {e}")
            return None