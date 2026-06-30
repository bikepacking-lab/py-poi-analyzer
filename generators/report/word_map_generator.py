#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class WordMapGenerator(BaseGenerator):
    """Générateur Word avec carte - AVEC CARTE"""
    
    def get_format_type(self) -> str:
        return 'docx-map'
    
    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        output_file = output_dir / f'analysis_report_{data.get("analysis_id", "unknown")}_map.docx'
        
        try:
            doc = Document()
            
            # ===== TITRE =====
            title = doc.add_heading('Rapport d\'Analyse GPS - AVEC CARTE', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # ===== INFORMATIONS GÉNÉRALES =====
            doc.add_heading('Informations générales', level=1)
            doc.add_paragraph(f'ID Analyse: {data.get("analysis_id", "N/A")}')
            doc.add_paragraph(f'Fichier: {data.get("input_file", "N/A")}')
            doc.add_paragraph(f'Date: {data.get("timestamp", "N/A")}')
            
            # ===== RÉSUMÉ =====
            summary = data.get('summary', {})
            track_info = summary.get('track_info', {})
            poi_search = summary.get('poi_search', {})
            poi_results = poi_search.get('results', {})
            performance = summary.get('performance', {})
            
            doc.add_heading('Résumé', level=1)
            doc.add_paragraph(f'Distance totale: {track_info.get("total_distance_km", 0)} km')
            doc.add_paragraph(f'Nombre de points: {track_info.get("total_points", 0)}')
            doc.add_paragraph(f'Total POI: {poi_results.get("total_found", 0)}')
            doc.add_paragraph(f'POI nommés: {poi_results.get("named_count", 0)}')
            doc.add_paragraph(f'POI non nommés: {poi_results.get("unnamed_count", 0)}')
            
            doc.add_heading('Performance', level=2)
            doc.add_paragraph(f'Temps total: {performance.get("total_duration_seconds", 0):.1f} secondes')
            doc.add_paragraph(f'Temps recherche POI: {performance.get("search_duration_seconds", 0):.1f} secondes')
            doc.add_paragraph(f'Temps calcul distances: {performance.get("distance_calculation_seconds", 0):.1f} secondes')
            
            # ===== CARTE =====
            doc.add_heading('Carte des POI', level=1)
            doc.add_paragraph('La carte ci-dessous montre la trace GPX et les POI détectés.')
            doc.add_paragraph('Légende: Bleu=Trace, Couleurs=POI par type')
            
            # Générer l'image de la carte
            map_image = self._create_map_image(data, output_dir)
            if map_image:
                try:
                    doc.add_picture(str(map_image), width=Inches(6))
                    doc.add_paragraph('')
                except Exception as e:
                    logger.error(f"Erreur insertion carte: {e}")
                    doc.add_paragraph('⚠️ Impossible d\'afficher la carte')
            else:
                doc.add_paragraph('⚠️ Carte non disponible')
            
            # ===== STATISTIQUES PAR TYPE =====
            by_type = poi_results.get('by_type', {})
            if by_type:
                doc.add_heading('Répartition par type', level=2)
                for poi_type, count in by_type.items():
                    doc.add_paragraph(f'{poi_type}: {count}', style='List Bullet')
            
            # ===== CONFIGURATION =====
            doc.add_heading('Configuration', level=2)
            config = poi_search.get('configuration', {})
            doc.add_paragraph(f'Types recherchés: {", ".join(config.get("types", []))}')
            doc.add_paragraph(f'Rayons: {config.get("radii", {})}')
            doc.add_paragraph(f'Intervalles: {config.get("intervals", {})}')
            
            # ===== TOUS LES POI =====
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
            return None
    
    def _create_map_image(self, data: Dict[str, Any], output_dir: Path) -> Optional[Path]:
        """Crée une image de la carte pour DOCX"""
        try:
            # Utiliser le générateur PDF Map
            from .pdf_map_generator import PDFMapGenerator
            
            pdf_map = PDFMapGenerator()
            pdf_file = pdf_map.generate(data, output_dir)
            
            if not pdf_file:
                return None
            
            # Convertir en image PNG
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(str(pdf_file), first_page=1, last_page=1)
                if images:
                    img_path = output_dir / 'map_preview.png'
                    images[0].save(str(img_path), 'PNG')
                    return img_path
            except ImportError:
                logger.warning("pdf2image non disponible")
                return None
                
        except Exception as e:
            logger.error(f"Erreur création image carte: {e}")
            return None
    
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