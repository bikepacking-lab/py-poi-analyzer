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
            return None

    def _build_content(self, data: Dict[str, Any]) -> List[Dict]:
        """Construit le contenu du document"""
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
                    'alignment': 'CENTER',
                    'spacingMode': 'NEVER_COLLAPSE',
                    'spaceAbove': {'magnitude': 12, 'unit': 'PT'},
                    'spaceBelow': {'magnitude': 6, 'unit': 'PT'}
                },
                'fields': 'namedStyleType,alignment,spacingMode,spaceAbove,spaceBelow'
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
                    'alignment': 'CENTER',
                    'spaceBelow': {'magnitude': 12, 'unit': 'PT'}
                },
                'fields': 'namedStyleType,alignment,spaceBelow'
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
                    'namedStyleType': 'HEADING_1',
                    'spaceAbove': {'magnitude': 18, 'unit': 'PT'},
                    'spaceBelow': {'magnitude': 6, 'unit': 'PT'}
                },
                'fields': 'namedStyleType,spaceAbove,spaceBelow'
            }
        })

        # Tableau de résumé
        summary_rows = [
            ['Métrique', 'Valeur'],
            ['Fichier source', data.get('input_file', 'N/A')],
            ['Distance totale', f"{track_info.get('total_distance_km', 0):.1f} km"],
            ['Points', str(track_info.get('total_points', 0))],
            ['POI trouvés', str(poi_results.get('total_found', 0))],
            ['POI nommés', str(poi_results.get('named_count', 0))],
            ['POI non nommés', str(poi_results.get('unnamed_count', 0))],
            ['Temps total', f"{performance.get('total_duration_seconds', 0):.1f} s"]
        ]

        # Créer le tableau
        requests.extend(self._create_table(summary_rows, current_index))
        current_index += self._get_table_length(summary_rows)

        # === SECTION 2: POI PAR TYPE ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "\n2. POI PAR TYPE\n"
            }
        })
        current_index += len("\n2. POI PAR TYPE\n")

        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len("\n2. POI PAR TYPE\n"),
                    'endIndex': current_index
                },
                'paragraphStyle': {
                    'namedStyleType': 'HEADING_1',
                    'spaceAbove': {'magnitude': 18, 'unit': 'PT'},
                    'spaceBelow': {'magnitude': 6, 'unit': 'PT'}
                },
                'fields': 'namedStyleType,spaceAbove,spaceBelow'
            }
        })

        # Tableau des types
        by_type = poi_results.get('by_type', {})
        if by_type:
            type_rows = [['Type de POI', 'Nombre']]
            for poi_type, count in by_type.items():
                type_rows.append([poi_type.capitalize(), str(count)])
            type_rows.append(['Total', str(poi_results.get('total_found', 0))])

            requests.extend(self._create_table(type_rows, current_index))
            current_index += self._get_table_length(type_rows)

        # === SECTION 3: CONFIGURATION ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "\n3. CONFIGURATION DE LA RECHERCHE\n"
            }
        })
        current_index += len("\n3. CONFIGURATION DE LA RECHERCHE\n")

        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len("\n3. CONFIGURATION DE LA RECHERCHE\n"),
                    'endIndex': current_index
                },
                'paragraphStyle': {
                    'namedStyleType': 'HEADING_1',
                    'spaceAbove': {'magnitude': 18, 'unit': 'PT'},
                    'spaceBelow': {'magnitude': 6, 'unit': 'PT'}
                },
                'fields': 'namedStyleType,spaceAbove,spaceBelow'
            }
        })

        # Configuration textuelle
        config_text = f"Types recherchés: {', '.join(config.get('types', []))}\n"
        config_text += f"Rayons: {json.dumps(config.get('radii', {}), ensure_ascii=False)}\n"
        config_text += f"Intervalles: {json.dumps(config.get('intervals', {}), ensure_ascii=False)}\n"

        # Filtres OSM
        osm_filters = config.get('osm_filters', {})
        if osm_filters:
            config_text += "\nFiltres OSM utilisés:\n"
            for poi_type, filters in osm_filters.items():
                config_text += f"\n  {poi_type.capitalize()}:\n"
                for f in filters[:5]:
                    config_text += f"    - {f}\n"
                if len(filters) > 5:
                    config_text += f"    ... et {len(filters) - 5} autres filtres\n"

        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': config_text
            }
        })
        current_index += len(config_text)

        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len(config_text),
                    'endIndex': current_index
                },
                'paragraphStyle': {
                    'namedStyleType': 'NORMAL_TEXT',
                    'spaceBelow': {'magnitude': 6, 'unit': 'PT'},
                    'fontSize': {'magnitude': 10, 'unit': 'PT'}
                },
                'fields': 'namedStyleType,spaceBelow,fontSize'
            }
        })

        # === SECTION 4: LISTE DES POI ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': f"\n4. LISTE DES POI ({len(pois)})\n"
            }
        })
        current_index += len(f"\n4. LISTE DES POI ({len(pois)})\n")

        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len(f"\n4. LISTE DES POI ({len(pois)})\n"),
                    'endIndex': current_index
                },
                'paragraphStyle': {
                    'namedStyleType': 'HEADING_1',
                    'spaceAbove': {'magnitude': 18, 'unit': 'PT'},
                    'spaceBelow': {'magnitude': 6, 'unit': 'PT'}
                },
                'fields': 'namedStyleType,spaceAbove,spaceBelow'
            }
        })

        if not pois:
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': "Aucun POI trouvé\n"
                }
            })
            current_index += len("Aucun POI trouvé\n")
        else:
            # Tableau des POI (compact)
            poi_rows = [['#', 'Type', 'Nom', 'Distance']]
            for i, poi in enumerate(pois[:100], 1):  # Limite à 100 dans le tableau
                poi_rows.append([
                    str(i),
                    self._safe_str(poi, 'type', '')[:12],
                    self._safe_str(poi, 'name', 'Sans nom')[:20],
                    f"{self._safe_float(poi, 'distance', 0.0):.2f} km"
                ])

            if len(pois) > 100:
                poi_rows.append(['', '...', f'... et {len(pois)-100} autres', ''])

            requests.extend(self._create_table(poi_rows, current_index, True))
            current_index += self._get_table_length(poi_rows)

        return requests

    def _create_table(self, rows: List[List[str]], start_index: int, compact: bool = False) -> List[Dict]:
        """Crée un tableau formaté"""
        if len(rows) < 2:
            return []

        requests = []
        num_cols = len(rows[0])

        # Insérer le tableau
        table_text = "\n" + "\n".join([" | ".join(row) for row in rows]) + "\n\n"
        requests.append({
            'insertText': {
                'location': {'index': start_index},
                'text': table_text
            }
        })

        # Style du tableau - pour Google Docs, on utilise des tabulations
        # et on applique des styles de paragraphe

        return requests

    def _get_table_length(self, rows: List[List[str]]) -> int:
        """Calcule la longueur du tableau en caractères"""
        if not rows:
            return 0
        return len("\n" + "\n".join([" | ".join(row) for row in rows]) + "\n\n")