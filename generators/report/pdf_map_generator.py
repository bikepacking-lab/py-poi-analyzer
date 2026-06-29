#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class PDFMapGenerator(BaseGenerator):
    
    def get_format_type(self) -> str:
        return 'pdf-map'
    
    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        output_file = output_dir / f'map_report_{data.get("analysis_id", "unknown")}.pdf'
        
        try:
            doc = SimpleDocTemplate(
                str(output_file),
                pagesize=landscape(A4),
                rightMargin=1*cm,
                leftMargin=1*cm,
                topMargin=1*cm,
                bottomMargin=1*cm
            )
            
            styles = getSampleStyleSheet()
            story = []
            
            # Titre
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                alignment=TA_CENTER,
                spaceAfter=20
            )
            story.append(Paragraph("Carte des POI", title_style))
            
            # RECUPERATION SECURISEE DES POIS
            pois = data.get('pois', [])
            if pois is None:
                pois = []
            
            if pois:
                # Tableau des POI
                table_data = [['#', 'Type', 'Nom', 'Lat', 'Lon', 'Dist (km)']]
                for i, poi in enumerate(pois[:30], 1):
                    # RECUPERATION SECURISEE DES VALEURS
                    poi_type = self._safe_get(poi, 'type', 'unknown')
                    poi_name = self._safe_get(poi, 'name', 'Sans nom')
                    poi_lat = self._safe_float(poi, 'lat', 0.0)
                    poi_lon = self._safe_float(poi, 'lon', 0.0)
                    poi_dist = self._safe_float(poi, 'distance', 0.0)
                    
                    table_data.append([
                        str(i),
                        str(poi_type),
                        str(poi_name)[:15],
                        f"{poi_lat:.4f}",
                        f"{poi_lon:.4f}",
                        f"{poi_dist:.2f}"
                    ])
                
                if len(pois) > 30:
                    table_data.append(['', '...', f'... {len(pois) - 30} autres', '', '', ''])
                
                table = Table(table_data, colWidths=[1*cm, 2*cm, 3.5*cm, 2.5*cm, 2.5*cm, 2*cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                ]))
                story.append(table)
                
                # Legende
                story.append(Spacer(1, 0.5*cm))
                story.append(Paragraph("Legende:", styles['Heading3']))
                
                poi_types = {}
                for poi in pois:
                    poi_type = self._safe_get(poi, 'type', 'unknown')
                    poi_types[poi_type] = poi_types.get(poi_type, 0) + 1
                
                for poi_type, count in poi_types.items():
                    story.append(Paragraph(f"• {poi_type}: {count}", styles['Normal']))
                
                story.append(Spacer(1, 0.5*cm))
                story.append(Paragraph(f"Total POI: {len(pois)}", styles['Normal']))
                
                # RECUPERATION SECURISEE DE LA DISTANCE
                total_distance = 0.0
                summary = data.get('summary', {})
                if isinstance(summary, dict):
                    track_info = summary.get('track_info', {})
                    if isinstance(track_info, dict):
                        total_distance = track_info.get('total_distance_km', 0)
                
                story.append(Paragraph(f"Distance: {total_distance:.2f} km", styles['Normal']))
            else:
                story.append(Paragraph("Aucun POI detecte", styles['Normal']))
            
            doc.build(story)
            logger.info(f"Carte PDF generee: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Erreur carte PDF: {e}")
            return None
    
    def _safe_get(self, obj: Any, key: str, default: str = '') -> str:
        """Recupere une valeur de maniere sure"""
        if obj is None:
            return default
        if isinstance(obj, dict):
            val = obj.get(key, default)
            return str(val) if val is not None else default
        if hasattr(obj, key):
            val = getattr(obj, key, default)
            return str(val) if val is not None else default
        return default
    
    def _safe_float(self, obj: Any, key: str, default: float = 0.0) -> float:
        """Recupere une valeur float de maniere sure"""
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