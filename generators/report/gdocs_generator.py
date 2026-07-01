#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import json

from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class GDocsGenerator(BaseGenerator):
    """Générateur de rapport Google Docs"""

    def __init__(self):
        super().__init__()
        self.service = None
        self.drive_service = None
        self._init_credentials()

    def get_format_type(self) -> str:
        return 'gdocs'

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
            logger.error("Installez: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
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
        """Génère un document Google Docs"""

        if not self.service:
            logger.error("Service Google non initialise")
            return None

        try:
            # 1. Créer le document
            doc_title = f"Rapport d'Analyse GPS - {data.get('analysis_id', 'unknown')[:8]}"

            doc = self.service.documents().create(body={'title': doc_title}).execute()
            doc_id = doc.get('documentId')
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

            logger.info(f"Document Google cree: {doc_title}")
            logger.info(f"URL: {doc_url}")

            # 2. Construire le contenu avec style
            requests = self._build_content(data)

            # 3. Mettre à jour le document
            if requests:
                for i in range(0, len(requests), 100):
                    batch = requests[i:i+100]
                    self.service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': batch}
                    ).execute()

            # 4. Sauvegarder l'URL
            url_file = output_dir / f'analysis_report_{data.get("analysis_id", "unknown")}_gdocs_url.txt'
            with open(url_file, 'w', encoding='utf-8') as f:
                f.write(doc_url)
                f.write('\n\n')
                f.write(f"Total POI: {len(data.get('pois', []))}")

            logger.info(f"URL Google Docs sauvegardee: {url_file}")

            return url_file

        except Exception as e:
            logger.error(f"Erreur generation Google Docs: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _build_content(self, data: Dict[str, Any]) -> List[Dict]:
        """Construit le contenu du document avec style professionnel"""
        requests = []
        current_index = 1

        summary = data.get('summary', {})
        track_info = summary.get('track_info', {})
        poi_search = summary.get('poi_search', {})
        poi_results = poi_search.get('results', {})
        performance = summary.get('performance', {})
        pois = data.get('pois', [])
        config = poi_search.get('configuration', {})

        # === TITRE PRINCIPAL ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "RAPPORT D'ANALYSE GPS\n"
            }
        })
        current_index += len("RAPPORT D'ANALYSE GPS\n")

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
        subtitle = f"ID: {data.get('analysis_id', 'N/A')} | {data.get('timestamp', '').split('T')[0]}\n\n"
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': subtitle
            }
        })
        current_index += len(subtitle)

        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len(subtitle),
                    'endIndex': current_index
                },
                'paragraphStyle': {
                    'namedStyleType': 'SUBTITLE',
                    'alignment': 'CENTER'
                },
                'fields': 'namedStyleType,alignment'
            }
        })

        # === SECTION 1: RESUME ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "1. RESUME DE L'ANALYSE\n"
            }
        })
        current_index += len("1. RESUME DE L'ANALYSE\n")

        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len("1. RESUME DE L'ANALYSE\n"),
                    'endIndex': current_index
                },
                'paragraphStyle': {
                    'namedStyleType': 'HEADING_1'
                },
                'fields': 'namedStyleType'
            }
        })

        # === CORRECTION: resume textuel bien construit ===
        total_ascent = track_info.get('total_ascent_m', 0)
        total_descent = track_info.get('total_descent_m', 0)
        min_elev = track_info.get('min_elevation_m', 'N/A')
        max_elev = track_info.get('max_elevation_m', 'N/A')

        resume_text = (
            f"Fichier source: {data.get('input_file', 'N/A')}\n"
            f"Distance totale: {track_info.get('total_distance_km', 0):.1f} km\n"
            f"Nombre de points: {track_info.get('total_points', 0)}\n"
            f"Denivele positif: {total_ascent:.0f} m\n"
            f"Denivele negatif: {total_descent:.0f} m\n"
            f"Altitude min: {min_elev} m\n"
            f"Altitude max: {max_elev} m\n"
            f"Total POI trouves: {poi_results.get('total_found', 0)}\n"
            f"POI nommes: {poi_results.get('named_count', 0)}\n"
            f"POI non nommes: {poi_results.get('unnamed_count', 0)}\n"
            f"Temps total: {performance.get('total_duration_seconds', 0):.1f} secondes\n\n"
        )

        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': resume_text
            }
        })
        current_index += len(resume_text)

        # === SECTION 2: POI PAR TYPE ===
        by_type = poi_results.get('by_type', {})
        if by_type:
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': "2. POI PAR TYPE\n"
                }
            })
            current_index += len("2. POI PAR TYPE\n")

            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index - len("2. POI PAR TYPE\n"),
                        'endIndex': current_index
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_1'
                    },
                    'fields': 'namedStyleType'
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

            # Total
            total_line = f"\nTotal: {poi_results.get('total_found', 0)} POI\n\n"
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': total_line
                }
            })
            current_index += len(total_line)

        # === SECTION 3: CONFIGURATION ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "3. CONFIGURATION DE LA RECHERCHE\n"
            }
        })
        current_index += len("3. CONFIGURATION DE LA RECHERCHE\n")

        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len("3. CONFIGURATION DE LA RECHERCHE\n"),
                    'endIndex': current_index
                },
                'paragraphStyle': {
                    'namedStyleType': 'HEADING_1'
                },
                'fields': 'namedStyleType'
            }
        })

        # Configuration
        config_text = f"Types recherches: {', '.join(config.get('types', []))}\n"
        config_text += f"Rayons: {json.dumps(config.get('radii', {}), ensure_ascii=False)}\n"
        config_text += f"Intervalles: {json.dumps(config.get('intervals', {}), ensure_ascii=False)}\n"

        # Filtres OSM (limités pour lisibilité)
        osm_filters = config.get('osm_filters', {})
        if osm_filters:
            config_text += "\nFiltres OSM utilises:\n"
            for poi_type, filters in osm_filters.items():
                config_text += f"\n  {poi_type.capitalize()}:\n"
                for f in filters[:3]:
                    config_text += f"    - {f}\n"
                if len(filters) > 3:
                    config_text += f"    ... et {len(filters) - 3} autres filtres\n"

        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': config_text + "\n"
            }
        })
        current_index += len(config_text) + 1

        # === SECTION 4: LISTE DES POI ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': f"4. LISTE DES POI ({len(pois)})\n"
            }
        })
        current_index += len(f"4. LISTE DES POI ({len(pois)})\n")

        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len(f"4. LISTE DES POI ({len(pois)})\n"),
                    'endIndex': current_index
                },
                'paragraphStyle': {
                    'namedStyleType': 'HEADING_1'
                },
                'fields': 'namedStyleType'
            }
        })

        if not pois:
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': "Aucun POI trouve\n"
                }
            })
            current_index += len("Aucun POI trouve\n")
        else:
            for i, poi in enumerate(pois, 1):
                name = self._safe_str(poi, 'name', 'Sans nom')
                poi_type = self._safe_str(poi, 'type', '')
                distance = self._safe_float(poi, 'distance', 0.0)
                address = self._safe_str(poi, 'address', '')
                phone = self._safe_str(poi, 'phone', '')
                
                line = f"{i}. {name}"
                if poi_type:
                    line += f" ({poi_type})"
                if distance > 0:
                    line += f" - {distance:.2f} km"
                line += "\n"
                
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': line
                    }
                })
                current_index += len(line)
                
                # Détails supplémentaires (indentés)
                details = []
                if address:
                    details.append(f"   Adresse: {address}")
                if phone:
                    details.append(f"   Tel: {phone}")
                
                for detail in details:
                    requests.append({
                        'insertText': {
                            'location': {'index': current_index},
                            'text': detail + "\n"
                        }
                    })
                    current_index += len(detail) + 1

        return requests