#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow non disponible. Installez: pip install Pillow")


class WordMapGenerator(BaseGenerator):
    """Générateur Word avec carte - Utilise Pillow pour générer l'image"""

    def get_format_type(self) -> str:
        return 'docx-map'

    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        output_file = output_dir / f'analysis_report_{data.get("analysis_id", "unknown")}_map.docx'

        if not PILLOW_AVAILABLE:
            logger.error("Pillow non installé. La carte ne peut pas être générée.")
            return None

        try:
            doc = Document()

            # === TITRE ===
            title = doc.add_heading('CARTE DES POI - TRACE GPS', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # === INFORMATIONS GENERALES ===
            doc.add_heading('Informations générales', level=1)
            doc.add_paragraph(f'ID Analyse: {data.get("analysis_id", "N/A")}')
            doc.add_paragraph(f'Fichier: {data.get("input_file", "N/A")}')
            doc.add_paragraph(f'Date: {data.get("timestamp", "N/A")}')

            # === RESUME AVEC DENIVELE ===
            summary = data.get('summary', {})
            track_info = summary.get('track_info', {})
            poi_search = summary.get('poi_search', {})
            poi_results = poi_search.get('results', {})
            performance = summary.get('performance', {})

            total_ascent = track_info.get('total_ascent_m', 0)
            total_descent = track_info.get('total_descent_m', 0)
            min_elev = track_info.get('min_elevation_m', 'N/A')
            max_elev = track_info.get('max_elevation_m', 'N/A')

            doc.add_heading('Résumé', level=1)
            doc.add_paragraph(f'Distance totale: {track_info.get("total_distance_km", 0)} km')
            doc.add_paragraph(f'Nombre de points: {track_info.get("total_points", 0)}')
            doc.add_paragraph(f'Dénivelé positif: {total_ascent:.0f} m')
            doc.add_paragraph(f'Dénivelé négatif: {total_descent:.0f} m')
            doc.add_paragraph(f'Altitude min: {min_elev} m')
            doc.add_paragraph(f'Altitude max: {max_elev} m')
            doc.add_paragraph(f'Total POI: {poi_results.get("total_found", 0)}')
            doc.add_paragraph(f'POI nommés: {poi_results.get("named_count", 0)}')
            doc.add_paragraph(f'POI non nommés: {poi_results.get("unnamed_count", 0)}')

            doc.add_heading('Performance', level=2)
            doc.add_paragraph(f'Temps total: {performance.get("total_duration_seconds", 0):.1f} secondes')
            doc.add_paragraph(f'Temps recherche POI: {performance.get("search_duration_seconds", 0):.1f} secondes')

            # === CARTE ===
            doc.add_heading('Carte des POI', level=1)
            doc.add_paragraph('Bleu=Trace | Couleurs=POI par type')

            # Générer l'image de la carte avec Pillow
            map_image = self._create_map_image(data, output_dir)

            if map_image and map_image.exists():
                try:
                    doc.add_page_break()
                    doc.add_picture(str(map_image), width=Inches(6.5))
                    doc.add_paragraph('')
                    logger.info(f"Carte ajoutée au document: {map_image}")
                except Exception as e:
                    logger.error(f"Erreur insertion carte: {e}")
                    doc.add_paragraph('⚠️ Impossible d\'afficher la carte')
            else:
                doc.add_paragraph('⚠️ Carte non générée')

            # === STATISTIQUES PAR TYPE ===
            by_type = poi_results.get('by_type', {})
            if by_type:
                doc.add_heading('Répartition par type', level=2)
                for poi_type, count in by_type.items():
                    doc.add_paragraph(f'{poi_type.capitalize()}: {count}', style='List Bullet')

            # === CONFIGURATION ===
            doc.add_heading('Configuration', level=2)
            config = poi_search.get('configuration', {})
            doc.add_paragraph(f'Types recherchés: {", ".join(config.get("types", []))}')
            doc.add_paragraph(f'Rayons: {config.get("radii", {})}')
            doc.add_paragraph(f'Intervalles: {config.get("intervals", {})}')

            # === TOUS LES POI ===
            doc.add_heading('Liste complète des POI', level=1)

            pois = data.get('pois', [])
            if not pois:
                doc.add_paragraph('Aucun POI trouvé')
            else:
                doc.add_paragraph(f'Total: {len(pois)} POI')
                doc.add_paragraph('')

                table = doc.add_table(rows=1, cols=9)
                table.style = 'Light Grid Accent 1'
                table.alignment = WD_TABLE_ALIGNMENT.CENTER

                headers = ['#', 'Type', 'Nom', 'Latitude', 'Longitude', 'Distance (km)', 'Adresse', 'Téléphone', 'Horaires']
                for i, header in enumerate(headers):
                    cell = table.rows[0].cells[i]
                    cell.text = header
                    if cell.paragraphs and cell.paragraphs[0] and cell.paragraphs[0].runs:
                        cell.paragraphs[0].runs[0].bold = True
                        cell.paragraphs[0].runs[0].font.size = Pt(9)

                for i, poi in enumerate(pois, 1):
                    row_cells = table.add_row().cells
                    row_cells[0].text = str(i)
                    row_cells[1].text = self._safe_str(poi, 'type', '')
                    row_cells[2].text = self._safe_str(poi, 'name', 'Sans nom')
                    row_cells[3].text = f"{self._safe_float(poi, 'lat', 0.0):.5f}"
                    row_cells[4].text = f"{self._safe_float(poi, 'lon', 0.0):.5f}"
                    row_cells[5].text = f"{self._safe_float(poi, 'distance', 0.0):.2f}"
                    row_cells[6].text = self._safe_str(poi, 'address', '')[:40]
                    row_cells[7].text = self._safe_str(poi, 'phone', '')
                    row_cells[8].text = self._safe_str(poi, 'opening_hours', '')[:20]

                logger.info(f"WordMap: {len(pois)} POI exportés")

            doc.save(str(output_file))
            logger.info(f"Rapport Word avec carte généré: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Erreur WordMap: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _create_map_image(self, data: Dict[str, Any], output_dir: Path) -> Optional[Path]:
        """Crée une image de la carte avec Pillow - Legende dynamique"""
        try:
            from PIL import Image, ImageDraw, ImageFont

            pois = data.get('pois', []) or []
            track_points = data.get('track_points', []) or []

            if not track_points and not pois:
                logger.warning("Aucune donnée pour la carte")
                return None

            # Dimensions de l'image
            img_width = 800
            img_height = 550
            margin = 50

            # Créer l'image
            img = Image.new('RGB', (img_width, img_height), color='#F8F9FA')
            draw = ImageDraw.Draw(img)

            # Bordures
            draw.rectangle(
                [margin-2, margin-2, img_width-margin+2, img_height-margin+2],
                outline='#2C3E50',
                width=2
            )

            # === COLLECTER LES COORDONNEES ===
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
                logger.warning("Pas de coordonnées valides")
                return None

            lat_min, lat_max = min(lats), max(lats)
            lon_min, lon_max = min(lons), max(lons)

            # Marge
            pad = max((lat_max - lat_min) * 0.08, 0.01)
            lat_min -= pad
            lat_max += pad
            lon_min -= pad
            lon_max += pad

            lat_range = lat_max - lat_min
            lon_range = lon_max - lon_min
            img_width_margin = img_width - 2 * margin
            img_height_margin = img_height - 2 * margin

            def to_pixel(lat, lon):
                x = margin + ((lon - lon_min) / lon_range) * img_width_margin
                y = margin + ((lat_max - lat) / lat_range) * img_height_margin
                return int(x), int(y)

            # === GRILLE ===
            grid_color = '#E8ECEF'
            for i in range(1, 5):
                r = i / 5.0
                lat = lat_min + lat_range * r
                lon = lon_min + lon_range * r
                _, y = to_pixel(lat, lon_min)
                x, _ = to_pixel(lat_min, lon)
                draw.line([(margin, y), (img_width - margin, y)], fill=grid_color, width=1)
                draw.line([(x, margin), (x, img_height - margin)], fill=grid_color, width=1)

            # === TRACE GPX ===
            track_pixels = []
            for p in track_points:
                lat = self._safe_float(p, 'latitude', 0.0)
                lon = self._safe_float(p, 'longitude', 0.0)
                if lat != 0 and lon != 0:
                    x, y = to_pixel(lat, lon)
                    track_pixels.append((x, y))

            if len(track_pixels) > 1:
                draw.line(track_pixels, fill='#2E86C1', width=3)

                step = max(1, len(track_pixels) // 80)
                for i in range(0, len(track_pixels), step):
                    x, y = track_pixels[i]
                    draw.ellipse([x-2, y-2, x+2, y+2], fill='#2E86C1')

            # === COULEURS DES POI ===
            poi_colors = {
                'water': '#3498DB',
                'refueling': '#E67E22',
                'bivouac': '#2ECC71',
                'accommodation': '#9B59B6',
                'bike-repair': '#E74C3C',
                'pharmacy': '#1ABC9C'
            }
            default_color = '#95A5A6'

            # === COMPTER LES TYPES PRESENTS ===
            types_presents = {}
            for poi in pois:
                poi_type = self._safe_str(poi, 'type', 'unknown')
                if poi_type not in types_presents:
                    types_presents[poi_type] = 0
                types_presents[poi_type] += 1

            try:
                font = ImageFont.truetype("arial.ttf", 10)
            except:
                font = ImageFont.load_default()

            # === DESSINER LES POI ===
            for idx, poi in enumerate(pois, 1):
                lat = self._safe_float(poi, 'lat', 0.0)
                lon = self._safe_float(poi, 'lon', 0.0)
                if lat == 0 and lon == 0:
                    continue

                x, y = to_pixel(lat, lon)
                poi_type = self._safe_str(poi, 'type', 'unknown')
                color = poi_colors.get(poi_type, default_color)
                name = self._safe_str(poi, 'name', '')

                # Cercle du POI
                draw.ellipse([x-7, y-7, x+7, y+7], fill=color, outline='white', width=2)

                # Numéro
                draw.text((x-4, y-5), str(idx), fill='white', font=font)

                # # Nom du POI
                # if name:
                #     draw.text((x+10, y-4), f"{idx}. {name[:15]}", fill='#2C3E50', font=font)

            # === ECHELLE ===
            dist_km = max(lat_range, lon_range) * 111
            dist_km = max(round(dist_km / 5) * 5, 1)

            sx, sy = margin + 20, img_height - margin - 20
            sw = min(60, img_width_margin * 0.12)

            draw.line([(sx, sy), (sx + int(sw), sy)], fill='#2C3E50', width=2)
            draw.line([(sx, sy-4), (sx, sy+4)], fill='#2C3E50', width=2)
            draw.line([(sx + int(sw), sy-4), (sx + int(sw), sy+4)], fill='#2C3E50', width=2)
            draw.text((sx + int(sw)//2 - 10, sy-18), f"{dist_km} km", fill='#2C3E50', font=font)

            # === LEGENDE - UNIQUEMENT LES TYPES PRESENTS ===
            if types_presents:
                lx = img_width - 160
                ly = margin + 10
                legend_height = 20 + len(types_presents) * 20 + 10

                draw.rectangle(
                    [lx, ly, lx + 130, ly + legend_height],
                    fill='white',
                    outline='#DDDDDD'
                )

                draw.text((lx + 8, ly + 5), "Légende", fill='#2C3E50', font=font)

                for j, (poi_type, count) in enumerate(types_presents.items()):
                    y2 = ly + 22 + j * 18
                    color = poi_colors.get(poi_type, default_color)
                    draw.rectangle([lx + 8, y2, lx + 18, y2 + 10], fill=color)
                    draw.text((lx + 24, y2 - 1), f"{poi_type.capitalize()} ({count})", fill='#2C3E50', font=font)

            # === SAUVEGARDE ===
            img_path = output_dir / f'docx_map_{data.get("analysis_id", "unknown")}.png'
            img.save(str(img_path), 'PNG', dpi=(150, 150))
            logger.info(f"Image de la carte générée: {img_path}")

            return img_path

        except Exception as e:
            logger.error(f"Erreur création image carte: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _safe_str(self, obj, key, default=''):
        if obj is None:
            return default
        if isinstance(obj, dict):
            val = obj.get(key, default)
            return str(val) if val is not None else default
        if hasattr(obj, key):
            val = getattr(obj, key, default)
            return str(val) if val is not None else default
        return default

    def _safe_float(self, obj, key, default=0.0):
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