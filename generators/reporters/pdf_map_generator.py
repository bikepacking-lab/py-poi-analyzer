#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, cast
import logging
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics.shapes import Drawing, Line, Circle, String, Rect
from reportlab.lib import colors
from ..base_generator import BaseGenerator



logger = logging.getLogger(__name__)

class PDFMapGenerator(BaseGenerator):
    """Génère une VRAIE carte avec trace GPX et POI - Affichage optimisé"""
    
    def get_format_type(self) -> str:
        return 'pdf-map'
    
    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        output_file = output_dir / f'analysis_report_{data.get("analysis_id", "unknown")}_map.pdf'
        
        try:
            # Récupération sécurisée des données
            pois = data.get('pois', []) or []
            track_points = data.get('track_points', []) or []
            
            if not track_points and not pois:
                logger.warning("Aucune donnée pour la carte")
                return None
            
            # Calcul des limites de la carte
            bounds = self._calculate_bounds(track_points, pois)
            if not bounds:
                logger.warning("Impossible de calculer les limites")
                return None
            
            # Création du document
            doc = SimpleDocTemplate(
                str(output_file),
                pagesize=landscape(A4),
                rightMargin=1*cm,
                leftMargin=1*cm,
                topMargin=1*cm,
                bottomMargin=1*cm
            )
            
            story = []
            styles = getSampleStyleSheet()
            
            # === TITRE ===
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                alignment=TA_CENTER,
                spaceAfter=8
            )
            story.append(Paragraph("CARTE DES POI - TRACE GPS", title_style))
            
            # === INFORMATIONS ===
            summary = data.get('summary', {})
            track_info = summary.get('track_info', {})
            total_dist = track_info.get('total_distance_km', 0)
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
            
            info_style = ParagraphStyle(
                'InfoStyle',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_CENTER,
                spaceAfter=12
            )
            story.append(Paragraph(
                f"Trace: {len(track_points)} points - {total_dist:.1f} km | POI: {len(pois)}",
                info_style
            ))
            
            # === CARTE ===
            map_drawing = self._create_map(bounds, track_points, pois)
            story.append(map_drawing)
            
            # === LÉGENDE DÉTAILLÉE ===
            story.append(Spacer(1, 0.3*cm))
            story.append(self._create_detailed_legend(pois))
            
            # === LISTE DES POI AVEC NUMÉROS ===
            story.append(PageBreak())
            story.append(Paragraph("LISTE DES POI", title_style))
            story.append(self._create_poi_list(pois))
            
            doc.build(story)
            
            logger.info(f"Carte PDF générée: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Erreur carte PDF: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _calculate_bounds(self, track_points: List[Dict], pois: List) -> Optional[Tuple[float, float, float, float]]:
        """Calcule les limites de la carte"""
        lats = []
        lons = []
        
        for p in track_points:
            lat = self._safe_float(p, 'latitude', 0.0)
            lon = self._safe_float(p, 'longitude', 0.0)
            if lat != 0 and lon != 0:
                lats.append(lat)
                lons.append(lon)
        
        for p in pois:
            lat = self._safe_float(p, 'lat', 0.0)
            lon = self._safe_float(p, 'lon', 0.0)
            if lat != 0 and lon != 0:
                lats.append(lat)
                lons.append(lon)
        
        if not lats or not lons:
            return None
        
        lat_min, lat_max = min(lats), max(lats)
        lon_min, lon_max = min(lons), max(lons)
        
        lat_range = max(lat_max - lat_min, 0.01)
        lon_range = max(lon_max - lon_min, 0.01)
        
        padding_lat = lat_range * 0.08
        padding_lon = lon_range * 0.08
        
        return (
            lat_min - padding_lat,
            lon_min - padding_lon,
            lat_max + padding_lat,
            lon_max + padding_lon
        )
    
    def _create_map(self, bounds: Tuple[float, float, float, float], 
                   track_points: List[Dict], pois: List) -> Drawing:
        """Crée le dessin de la carte avec affichage optimisé"""
        lat_min, lon_min, lat_max, lon_max = bounds
        
        map_width = 720
        map_height = 420
        margin = 25
        
        drawing = Drawing(map_width, map_height)
        
        # Fond
        bg = Rect(
            margin, margin,
            map_width - 2*margin, 
            map_height - 2*margin
        )
        bg.fillColor=colors.HexColor('#F8F9FA')
        bg.strokeColor=colors.HexColor('#2C3E50')
        bg.strokeWidth=1.5
        drawing.add(bg)
        
        def to_pixel(lat, lon):
            x = margin + ((lon - lon_min) / (lon_max - lon_min)) * (map_width - 2*margin)
            y = margin + ((lat - lat_min) / (lat_max - lat_min)) * (map_height - 2*margin)
            return x, y
        
        # === 1. GRILLE ===
        for i in range(1, 5):
            ratio = i / 5.0
            # Horizontale
            lat = lat_min + (lat_max - lat_min) * ratio
            _, y = to_pixel(lat, lon_min)
            line = Line(margin, y, map_width - margin, y)
            line.strokeColor = colors.HexColor('#E8ECEF')
            line.strokeWidth = 0.5
            drawing.add(line)
            
            # Verticale
            lon = lon_min + (lon_max - lon_min) * ratio
            x, _ = to_pixel(lat_min, lon)
            line = Line(x, margin, x, map_height - margin)
            line.strokeColor = colors.HexColor('#E8ECEF')
            line.strokeWidth = 0.5
            drawing.add(line)
        
        # === 2. TRACE GPX ===
        track_points_filtered = []
        for p in track_points:
            lat = self._safe_float(p, 'latitude', 0.0)
            lon = self._safe_float(p, 'longitude', 0.0)
            if lat != 0 and lon != 0:
                track_points_filtered.append((lat, lon))
        
        if len(track_points_filtered) > 1:
            # Ligne de la trace
            for i in range(len(track_points_filtered) - 1):
                lat1, lon1 = track_points_filtered[i]
                lat2, lon2 = track_points_filtered[i+1]
                x1, y1 = to_pixel(lat1, lon1)
                x2, y2 = to_pixel(lat2, lon2)
                
                line = Line(x1, y1, x2, y2)
                line.strokeColor = colors.HexColor('#2E86C1')
                line.strokeWidth = 3
                drawing.add(line)
            
            # Points de la trace
            step = max(1, len(track_points_filtered) // 80)
            for i in range(0, len(track_points_filtered), step):
                lat, lon = track_points_filtered[i]
                x, y = to_pixel(lat, lon)
                circle = Circle(x, y, 2)
                circle.fillColor = colors.HexColor('#2E86C1')
                circle.strokeColor = colors.HexColor('#2E86C1')
                drawing.add(circle)
        
        # === 3. POI AVEC NUMÉROS ===
        poi_colors = {
            'water': {'fill': '#3498DB', 'text': '#2874A6'},
            'refueling': {'fill': '#E67E22', 'text': '#CA6F1E'},
            'bivouac': {'fill': '#2ECC71', 'text': '#1E8449'},
            'accommodation': {'fill': '#9B59B6', 'text': '#6C3483'},
            'bike-repair': {'fill': '#E74C3C', 'text': '#B03A2E'},
            'pharmacy': {'fill': '#1ABC9C', 'text': '#0E6655'}
        }
        
        # Filtrer et numéroter les POI
        valid_pois = []
        for poi in pois:
            lat = self._safe_float(poi, 'lat', 0.0)
            lon = self._safe_float(poi, 'lon', 0.0)
            if lat != 0 and lon != 0:
                valid_pois.append((poi, lat, lon))
        
        for idx, (poi, lat, lon) in enumerate(valid_pois, 1):
            x, y = to_pixel(lat, lon)
            poi_type = self._safe_str(poi, 'type', 'unknown')
            # poi_name = self._safe_str(poi, 'name', '')
            
            colors_info = poi_colors.get(poi_type, {'fill': '#95A5A6', 'text': '#5D6D7E'})
            
            # Cercle du POI (plus gros)
            circle = Circle(x, y, 7)
            circle.fillColor = colors.HexColor(colors_info['fill'])
            circle.strokeColor = colors.white
            circle.strokeWidth = 2
            drawing.add(circle)
            
            # Numéro du POI (blanc sur le cercle)
            num_str = String(x, y - 3, str(idx))
            num_str.fontName = 'Helvetica-Bold'
            num_str.fontSize = 8
            num_str.fillColor = colors.white
            num_str.textAnchor = 'middle'
            drawing.add(num_str)
            
            # # Petite ligne de connexion pour le nom
            # if poi_name:
            #     # Fond blanc pour le texte
            #     name_str = String(x + 10, y + 2, f"{idx}. {poi_name[:20]}")
            #     name_str.fontName = 'Helvetica'
            #     name_str.fontSize = 7
            #     name_str.fillColor = colors.HexColor('#2C3E50')
                
            #     # S'assurer que le texte reste dans la carte
            #     if x + 10 + len(poi_name[:20]) * 4 > map_width - margin:
            #         # Texte à gauche
            #         name_str.x = x - 10 - len(poi_name[:20]) * 4
            #     drawing.add(name_str)
        
        # === 4. ÉCHELLE ===
        # Calcul de l'échelle approximative
        lat_span = lat_max - lat_min
        lon_span = lon_max - lon_min
        scale_km = max(lat_span, lon_span) * 111  # 1 degré ~ 111 km
        scale_km = round(scale_km / 10) * 10  # Arrondi à 10 près
        if scale_km < 1:
            scale_km = 1
        
        # Barre d'échelle
        scale_x = margin + 20
        scale_y = margin + 15
        scale_width = 50
        
        # Ligne
        line = Line(scale_x, scale_y, scale_x + scale_width, scale_y)
        line.strokeColor = colors.HexColor('#2C3E50')
        line.strokeWidth = 2
        drawing.add(line)
        
        # Petites barres verticales
        for x in [scale_x, scale_x + scale_width]:
            vline = Line(x, scale_y - 3, x, scale_y + 3)
            vline.strokeColor = colors.HexColor('#2C3E50')
            vline.strokeWidth = 1
            drawing.add(vline)
        
        # Texte de l'échelle
        scale_text = String(scale_x + scale_width/2, scale_y - 8, f"{scale_km} km")
        scale_text.fontName = 'Helvetica'
        scale_text.fontSize = 7
        scale_text.fillColor = colors.HexColor('#2C3E50')
        scale_text.textAnchor = 'middle'
        drawing.add(scale_text)
        
        return drawing
    
    def _create_detailed_legend(self, pois: List) -> Table:
        """Crée une légende détaillée avec les numéros"""
        if not pois:
            return Table([['Aucun POI']])
        
        # Compter les types
        poi_types = {}
        for poi in pois:
            poi_type = self._safe_str(poi, 'type', 'unknown')
            poi_types[poi_type] = poi_types.get(poi_type, 0) + 1
        
        # Couleurs
        colors_map = {
            'water': '🔵 Eau',
            'refueling': '🟠 Ravitaillement',
            'bivouac': '🟢 Bivouac',
            'accommodation': '🟣 Hébergement',
            'bike-repair': '🔴 Réparation vélo',
            'pharmacy': '🩵 Pharmacie'
        }
        
        legend_data = [['Type', 'Couleur', 'Nombre']]
        for poi_type, count in poi_types.items():
            color_desc = colors_map.get(poi_type, f'• {poi_type}')
            legend_data.append([color_desc, '', str(count)])
        
        legend_data.append(['Total', '', str(len(pois))])
        
        table = Table(legend_data, colWidths=[4*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#F8F9FA')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
        ]))
        
        return table
    
    def _create_poi_list(self, pois: List) -> Table:
        """Crée la liste détaillée des POI avec numéros"""
        if not pois:
            return Table([['Aucun POI']])
        
        # Filtrer les POI valides
        valid_pois = []
        for poi in pois:
            lat = self._safe_float(poi, 'lat', 0.0)
            lon = self._safe_float(poi, 'lon', 0.0)
            if lat != 0 and lon != 0:
                valid_pois.append(poi)
        
        if not valid_pois:
            return Table([['Aucun POI valide']])
        
        # Tableau des POI
        data = [['#', 'Type', 'Nom', 'Latitude', 'Longitude', 'Distance (km)']]
        
        for idx, poi in enumerate(valid_pois, 1):
            poi_type = self._safe_str(poi, 'type', '')
            poi_name = self._safe_str(poi, 'name', 'Sans nom')
            poi_lat = self._safe_float(poi, 'lat', 0.0)
            poi_lon = self._safe_float(poi, 'lon', 0.0)
            poi_dist = self._safe_float(poi, 'distance_along_track', self._safe_float(poi, 'distance', 0.0))
            
            data.append([
                str(idx),
                poi_type[:15],
                poi_name[:25],
                f"{poi_lat:.5f}",
                f"{poi_lon:.5f}",
                f"{poi_dist:.2f}" if poi_dist > 0 else ""
            ])
        
        table = Table(data, colWidths=[0.8*cm, 2.5*cm, 4*cm, 2.5*cm, 2.5*cm, 2*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        return table
    
    def _safe_str(self, obj: Any, key: str, default: str = '') -> str:
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