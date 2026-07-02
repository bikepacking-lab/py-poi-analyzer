#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class KMLConverter(BaseGenerator):
    """Convertisseur KML sans POI"""

    def get_format_type(self) -> str:
        return 'kml'

    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        """Génère un KML sans POI"""
        try:
            track_points = data.get('track_points', [])
            
            if not track_points:
                logger.warning("Aucun point de trace pour le KML")
                return None

            kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
            document = ET.SubElement(kml, 'Document')
            
            name = ET.SubElement(document, 'name')
            name.text = 'Trace GPS'
            
            # Style
            style = ET.SubElement(document, 'Style', id='trackStyle')
            line_style = ET.SubElement(style, 'LineStyle')
            color = ET.SubElement(line_style, 'color')
            color.text = 'ff0000ff'
            width = ET.SubElement(line_style, 'width')
            width.text = '4'
            
            # Placemark
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
            
            xml_str = minidom.parseString(ET.tostring(kml)).toprettyxml(indent="  ")
            
            analysis_id = data.get('analysis_id', 'unknown')
            output_file = output_dir / f"converted_track_{analysis_id}.kml"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_str)
            
            logger.info(f"KML genere: {output_file} ({len(track_points)} points)")
            return output_file
            
        except Exception as e:
            logger.error(f"Erreur KML: {e}")
            return None