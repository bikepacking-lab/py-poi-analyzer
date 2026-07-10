#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from core import gpx_processor

from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class PDFGenerator(BaseGenerator):
    
    def get_format_type(self) -> str:
        return 'pdf'
    
    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        output_file = output_dir / f'analysis_report_{data.get("analysis_id", "unknown")}.pdf'
        
        try:
            doc = SimpleDocTemplate(
                str(output_file),
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            styles = self._get_styles()
            story = []
            
            # 1. Page de garde
            story.extend(self._create_cover_page(data, styles))
            story.append(PageBreak())
            
            # 2. Resume
            story.extend(self._create_summary_section(data, styles))
            story.append(PageBreak())
            
            # 3. Liste des POI
            story.extend(self._create_poi_section(data, styles))
            
            doc.build(story)
            
            logger.info(f"Rapport PDF genere: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Erreur PDF: {e}")
            return None
    
    def _get_styles(self):
        """Cree les styles pour le PDF"""
        styles = getSampleStyleSheet()
        
        # Style personnalise pour le titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=colors.HexColor('#1B4F72')
        )
        
        # Style pour les sous-titres
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=18,
            alignment=TA_LEFT,
            spaceAfter=12,
            textColor=colors.HexColor('#2E86C1')
        )
        
        # Style pour les informations
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=4
        )
        
        # Style pour les POI
        poi_style = ParagraphStyle(
            'POIStyle',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_LEFT,
            spaceAfter=6,
            leading=12
        )
        
        return {
            'title': title_style,
            'subtitle': subtitle_style,
            'info': info_style,
            'poi': poi_style,
            'normal': styles['Normal'],
            'heading2': styles['Heading2'],
            'heading3': styles['Heading3']
        }
    
    def _create_cover_page(self, data, styles):
        """Cree la page de garde"""
        story = []
        
        # Espacement
        story.append(Spacer(1, 4*cm))
        
        # Titre principal
        story.append(Paragraph("RAPPORT D'ANALYSE GPS", styles['title']))
        story.append(Spacer(1, 1*cm))
        
        # Sous-titre
        story.append(Paragraph("Points d'Interet et Analyse de Trace", styles['subtitle']))
        story.append(Spacer(1, 3*cm))
        
        # Informations
        summary = data.get('summary', {})
        track_info = summary.get('track_info', {})
        
        info_lines = [
            f"ID Analyse: {data.get('analysis_id', '')}",
            f"Fichier: {data.get('input_file', '')}",
            f"Date: {data.get('timestamp', '')}",
            f"Distance: {track_info.get('total_distance_km', 0)} km",
            f"Points: {track_info.get('total_points', 0)}",
            f"POI Trouves: {len(data.get('pois', []))}"
        ]
        
        for line in info_lines:
            story.append(Paragraph(line, styles['info']))
            story.append(Spacer(1, 0.2*cm))
        
        return story
    
    def _create_summary_section(self, data, styles):
        story = []
    
        story.append(Paragraph("1. RESUME DE L'ANALYSE", styles['subtitle']))
        story.append(Spacer(1, 0.5*cm))
    
        summary = data.get('summary', {})
        track_info = summary.get('track_info', {})
        poi_search = summary.get('poi_search', {})
        poi_results = poi_search.get('results', {})
        performance = summary.get('performance', {})
        time_est = summary.get('time_estimate', {})
        
        resume_data = [
            ['Metrique', 'Valeur'],
            ['Distance totale', f"{track_info.get('total_distance_km', 0)} km"],
            ['Nombre de points', str(track_info.get('total_points', 0))],
            ['Segments', str(data.get('num_segments', 1))],
            ['Total POI', str(poi_results.get('total_found', 0))],
            ['POI nommes', str(poi_results.get('named_count', 0))],
            ['POI non nommes', str(poi_results.get('unnamed_count', 0))],
            ['Temps total', f"{performance.get('total_duration_seconds', 0):.1f} s"],
            ['Temps recherche POI', f"{performance.get('search_duration_seconds', 0):.1f} s"],
            ['Temps calcul distances', f"{performance.get('distance_calculation_seconds', 0):.1f} s"],
            ['Denivele positif', f"{track_info.get('total_ascent_m', 0)} m"],
            ['Denivele negatif', f"{track_info.get('total_descent_m', 0)} m"],
            ['Altitude min', f"{track_info.get('min_elevation_m', 'N/A')} m"],
            ['Altitude max', f"{track_info.get('max_elevation_m', 'N/A')} m"],
            ['Temps estime', f"{time_est.get('formatted_moving', 'N/A')} h"],
            ['Avec pauses', f"{time_est.get('formatted_total', 'N/A')} h"],
            ['Temps estime (humain)', f"{time_est.get('formatted_moving_dhm', 'N/A')} h"],
            ['Avec pauses (humain)', f"{time_est.get('formatted_total_dhm', 'N/A')} h"],
            ['Vitesse moyenne', f"{time_est.get('average_speed_kmh', 'N/A')} km/h"],
            ['Allure moyenne', f"{time_est.get('pace_min_per_km', 'N/A')} min/km"]
        ]
    
        table = Table(resume_data, colWidths=[6*cm, 8*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B4F72')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(table)
    
        return story
    
    def _create_poi_section(self, data, styles):
        """Cree la section des POI"""
        story = []
        
        pois = data.get('pois', [])
        
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(f"2. POI DETECTES ({len(pois)})", styles['subtitle']))
        story.append(Spacer(1, 0.5*cm))
        
        if not pois:
            story.append(Paragraph("Aucun Point d'Interet trouve", styles['normal']))
            return story
        
        # Statistiques par type
        by_type = {}
        for poi in pois:
            poi_type = poi.get('type', 'unknown')
            by_type[poi_type] = by_type.get(poi_type, 0) + 1
        
        story.append(Paragraph("Repartition par type:", styles['heading3']))
        type_data = [['Type', 'Nombre']]
        for poi_type, count in by_type.items():
            type_data.append([poi_type, str(count)])
        
        table = Table(type_data, colWidths=[6*cm, 4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86C1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(table)
        story.append(Spacer(1, 1*cm))
        
        # Liste detaillee des POI
        story.append(Paragraph("Details des POI:", styles['heading3']))
        story.append(Spacer(1, 0.3*cm))
        
        for i, poi in enumerate(pois, 1):
            story.append(Paragraph(f"{i}. {poi.get('name', 'Sans nom')}", styles['heading3']))
            
            details = []
            if poi.get('type'):
                details.append(f"Type: {poi.get('type')}")
            if poi.get('distance'):
                details.append(f"Distance: {poi.get('distance'):.2f} km")
            if poi.get('address'):
                details.append(f"Adresse: {poi.get('address')}")
            if poi.get('phone'):
                details.append(f"Tel: {poi.get('phone')}")
            if poi.get('opening_hours'):
                details.append(f"Horaires: {poi.get('opening_hours')}")
            if poi.get('description'):
                details.append(f"Description: {poi.get('description')}")
            if poi.get('google_maps_url'):
                details.append(f"Google Maps: {poi.get('google_maps_url')}")
            if poi.get('overpass_url'):
                details.append(f"Overpass: {poi.get('overpass_url')}")
            
            for detail in details:
                story.append(Paragraph(f"  - {detail}", styles['poi']))
            
            story.append(Spacer(1, 0.2*cm))
        
        # if len(pois) > 50:
        #     story.append(Paragraph(f"... et {len(pois) - 50} autres POI", styles['normal']))
        
        return story