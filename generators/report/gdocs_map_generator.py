#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow non disponible. Installez: pip install Pillow")


class GDocsMapGenerator(BaseGenerator):
    """Générateur Google Docs avec carte intégrée"""

    def __init__(self):
        super().__init__()
        self.service = None
        self.drive_service = None
        self._init_credentials()

    def get_format_type(self) -> str:
        return 'gdocs-map'

    def _init_credentials(self):
        """Initialise les credentials Google"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            SCOPES = [
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/drive.file'
            ]

            creds = None
            token_path = self._get_token_path()
            credentials_path = self._get_credentials_path()

            if token_path.exists():
                try:
                    with open(token_path, 'r') as f:
                        creds = Credentials.from_authorized_user_info(
                            json.load(f), SCOPES
                        )
                except Exception as e:
                    logger.warning(f"Erreur chargement token: {e}")

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    logger.info("Token Google refresh")
                else:
                    if not credentials_path.exists():
                        logger.error(
                            "Fichier credentials.json non trouve. "
                            "Veuillez le placer dans: " + str(credentials_path)
                        )
                        return

                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("Authentification Google reussie")

                with open(token_path, 'w') as f:
                    json.dump(json.loads(creds.to_json()), f)
                logger.info(f"Token Google sauvegarde: {token_path}")

            self.service = build('docs', 'v1', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            logger.info("Services Google initialises")

        except ImportError as e:
            logger.error(f"Bibliotheques Google manquantes: {e}")
        except Exception as e:
            logger.error(f"Erreur initialisation Google: {e}")

    def _get_credentials_path(self) -> Path:
        from config import BASE_DIR
        creds_dir = BASE_DIR / 'credentials'
        creds_dir.mkdir(exist_ok=True)
        return creds_dir / 'credentials.json'

    def _get_token_path(self) -> Path:
        from config import BASE_DIR
        creds_dir = BASE_DIR / 'credentials'
        creds_dir.mkdir(exist_ok=True)
        return creds_dir / 'token_gdocs.json'

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

    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        """Génère un document Google Docs avec carte intégrée"""

        if not PILLOW_AVAILABLE:
            logger.error("Pillow non installe. Impossible de generer la carte.")
            return None

        if not self.service:
            logger.error("Service Google non initialise")
            return None

        try:
            # 1. Créer le document
            doc_title = f"Rapport d'Analyse GPS avec Carte - {data.get('analysis_id', 'unknown')[:8]}"

            doc = self.service.documents().create(body={'title': doc_title}).execute()
            doc_id = doc.get('documentId')
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

            logger.info(f"Document Google cree: {doc_title}")
            logger.info(f"URL: {doc_url}")

            # 2. Générer l'image de la carte
            map_image_path = self._create_map_image(data, output_dir)

            # 3. Construire le contenu
            requests = self._build_content(data, map_image_path)

            # 4. Mettre à jour le document
            if requests:
                for i in range(0, len(requests), 100):
                    batch = requests[i:i+100]
                    self.service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': batch}
                    ).execute()

            # 5. Sauvegarder l'URL
            url_file = output_dir / f'analysis_report_{data.get("analysis_id", "unknown")}_gdocs_map_url.txt'
            with open(url_file, 'w', encoding='utf-8') as f:
                f.write(doc_url)
                f.write('\n\n')
                f.write(f"Total POI: {len(data.get('pois', []))}")

            logger.info(f"URL Google Docs avec carte sauvegardee: {url_file}")

            return url_file

        except Exception as e:
            logger.error(f"Erreur generation Google Docs avec carte: {e}")
            return None

    def _create_map_image(self, data: Dict[str, Any], output_dir: Path) -> Optional[Path]:
        """Crée une image de la carte avec Pillow"""
        try:
            from PIL import Image, ImageDraw, ImageFont

            pois = data.get('pois', []) or []
            track_points = data.get('track_points', []) or []

            if not track_points and not pois:
                return None

            # Dimensions de l'image
            img_width = 800
            img_height = 550
            margin = 50

            img = Image.new('RGB', (img_width, img_height), color='#F8F9FA')
            draw = ImageDraw.Draw(img)

            # Bordures
            draw.rectangle(
                [margin-2, margin-2, img_width-margin+2, img_height-margin+2],
                outline='#2C3E50',
                width=2
            )

            # Collecter les coordonnées
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

            # Grille
            grid_color = '#E8ECEF'
            for i in range(1, 5):
                r = i / 5.0
                lat = lat_min + lat_range * r
                lon = lon_min + lon_range * r
                _, y = to_pixel(lat, lon_min)
                x, _ = to_pixel(lat_min, lon)
                draw.line([(margin, y), (img_width - margin, y)], fill=grid_color, width=1)
                draw.line([(x, margin), (x, img_height - margin)], fill=grid_color, width=1)

            # Trace GPX
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

            # POI
            poi_colors = {
                'water': '#3498DB',
                'refueling': '#E67E22',
                'bivouac': '#2ECC71',
                'accommodation': '#9B59B6',
                'bike-repair': '#E74C3C',
                'pharmacy': '#1ABC9C'
            }

            try:
                font = ImageFont.truetype("arial.ttf", 10)
            except:
                font = ImageFont.load_default()

            for idx, poi in enumerate(pois, 1):
                lat = self._safe_float(poi, 'lat', 0.0)
                lon = self._safe_float(poi, 'lon', 0.0)
                if lat == 0 and lon == 0:
                    continue

                x, y = to_pixel(lat, lon)
                poi_type = self._safe_str(poi, 'type', 'unknown')
                color = poi_colors.get(poi_type, '#95A5A6')
                name = self._safe_str(poi, 'name', '')

                draw.ellipse([x-7, y-7, x+7, y+7], fill=color, outline='white', width=2)
                draw.text((x-4, y-5), str(idx), fill='white', font=font)

                if name:
                    draw.text((x+10, y-4), f"{idx}. {name[:15]}", fill='#2C3E50', font=font)

            # Échelle
            dist_km = max(lat_range, lon_range) * 111
            dist_km = max(round(dist_km / 5) * 5, 1)

            sx, sy = margin + 20, img_height - margin - 20
            sw = min(60, img_width_margin * 0.12)

            draw.line([(sx, sy), (sx + int(sw), sy)], fill='#2C3E50', width=2)
            draw.line([(sx, sy-4), (sx, sy+4)], fill='#2C3E50', width=2)
            draw.line([(sx + int(sw), sy-4), (sx + int(sw), sy+4)], fill='#2C3E50', width=2)
            draw.text((sx + int(sw)//2 - 10, sy-18), f"{dist_km} km", fill='#2C3E50', font=font)

            # Légende
            lx = img_width - 160
            ly = margin + 10
            legend_height = 20 + len(poi_colors) * 20 + 10

            draw.rectangle(
                [lx, ly, lx + 130, ly + legend_height],
                fill='white',
                outline='#DDDDDD'
            )

            draw.text((lx + 8, ly + 5), "Légende", fill='#2C3E50', font=font)

            for j, (typ, col) in enumerate(poi_colors.items()):
                y2 = ly + 22 + j * 18
                draw.rectangle([lx + 8, y2, lx + 18, y2 + 10], fill=col)
                draw.text((lx + 24, y2 - 1), typ, fill='#2C3E50', font=font)

            # Sauvegarde
            img_path = output_dir / f'gdocs_map_{data.get("analysis_id", "unknown")}.png'
            img.save(str(img_path), 'PNG', dpi=(150, 150))
            logger.info(f"Image de la carte generee: {img_path}")

            return img_path

        except Exception as e:
            logger.error(f"Erreur creation image carte: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _build_content(self, data: Dict[str, Any], map_image_path: Optional[Path]) -> List[Dict]:
        """Construit le contenu du document avec carte intégrée"""
        requests = []
        current_index = 1

        summary = data.get('summary', {})
        track_info = summary.get('track_info', {})
        poi_search = summary.get('poi_search', {})
        poi_results = poi_search.get('results', {})
        performance = summary.get('performance', {})
        pois = data.get('pois', [])
        config = poi_search.get('configuration', {})

        # === TITRE ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "RAPPORT D'ANALYSE GPS - AVEC CARTE\n"
            }
        })
        current_index += len("RAPPORT D'ANALYSE GPS - AVEC CARTE\n")

        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': 1,
                    'endIndex': current_index
                },
                'paragraphStyle': {
                    'namedStyleType': 'TITLE',
                    'alignment': 'CENTER'
                },
                'fields': 'namedStyleType,alignment'
            }
        })

        # === SOUS-TITRE ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': f"ID: {data.get('analysis_id', 'N/A')} | {data.get('timestamp', '').split('T')[0]}\n\n"
            }
        })
        current_index += len(f"ID: {data.get('analysis_id', 'N/A')} | {data.get('timestamp', '').split('T')[0]}\n\n")

        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len(f"ID: {data.get('analysis_id', 'N/A')} | {data.get('timestamp', '').split('T')[0]}\n\n"),
                    'endIndex': current_index
                },
                'paragraphStyle': {
                    'namedStyleType': 'SUBTITLE',
                    'alignment': 'CENTER'
                },
                'fields': 'namedStyleType,alignment'
            }
        })

        # === CARTE ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "CARTE DES POI\n\n"
            }
        })
        current_index += len("CARTE DES POI\n\n")

        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len("CARTE DES POI\n\n"),
                    'endIndex': current_index
                },
                'paragraphStyle': {
                    'namedStyleType': 'HEADING_1',
                    'spaceAbove': {'magnitude': 18, 'unit': 'PT'}
                },
                'fields': 'namedStyleType,spaceAbove'
            }
        })

        # Insérer l'image de la carte
        if map_image_path and map_image_path.exists():
            # Google Docs API nécessite une image encodée en base64
            try:
                import base64
                with open(map_image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')

                # Insérer l'image
                requests.append({
                    'insertInlineImage': {
                        'location': {'index': current_index},
                        'uri': f'data:image/png;base64,{image_data}',
                        'objectSize': {
                            'height': {'magnitude': 400, 'unit': 'PT'},
                            'width': {'magnitude': 600, 'unit': 'PT'}
                        }
                    }
                })
                current_index += 1  # L'image prend un caractère

                # Légende de la carte
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': '\nLégende: Bleu=Trace | Couleurs=POI par type\n\n'
                    }
                })
                current_index += len('\nLégende: Bleu=Trace | Couleurs=POI par type\n\n')

            except Exception as e:
                logger.error(f"Erreur insertion image: {e}")
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': '⚠️ Image de la carte non disponible\n\n'
                    }
                })
                current_index += len('⚠️ Image de la carte non disponible\n\n')

        # === RESUME ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "RESUME DE L'ANALYSE\n"
            }
        })
        current_index += len("RESUME DE L'ANALYSE\n")

        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len("RESUME DE L'ANALYSE\n"),
                    'endIndex': current_index
                },
                'paragraphStyle': {
                    'namedStyleType': 'HEADING_1',
                    'spaceAbove': {'magnitude': 18, 'unit': 'PT'}
                },
                'fields': 'namedStyleType,spaceAbove'
            }
        })

        # Résumé textuel
        resume_text = (
            f"Fichier: {data.get('input_file', 'N/A')}\n"
            f"Distance totale: {track_info.get('total_distance_km', 0):.1f} km\n"
            f"Points: {track_info.get('total_points', 0)}\n"
            f"POI trouves: {poi_results.get('total_found', 0)}\n"
            f"POI nommes: {poi_results.get('named_count', 0)}\n"
            f"POI non nommes: {poi_results.get('unnamed_count', 0)}\n"
            f"Temps total: {performance.get('total_duration_seconds', 0):.1f} s\n\n"
        )
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': resume_text
            }
        })
        current_index += len(resume_text)

        # === STATISTIQUES PAR TYPE ===
        by_type = poi_results.get('by_type', {})
        if by_type:
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': "POI PAR TYPE\n"
                }
            })
            current_index += len("POI PAR TYPE\n")

            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index - len("POI PAR TYPE\n"),
                        'endIndex': current_index
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_2',
                        'spaceAbove': {'magnitude': 12, 'unit': 'PT'}
                    },
                    'fields': 'namedStyleType,spaceAbove'
                }
            })

            for poi_type, count in by_type.items():
                line = f"  - {poi_type.capitalize()}: {count}\n"
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': line
                    }
                })
                current_index += len(line)

            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': '\n'
                }
            })
            current_index += 1

        return requests