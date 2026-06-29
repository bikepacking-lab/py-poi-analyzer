#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import json
from config import BASE_DIR
        
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class GDocsGenerator(BaseGenerator):
    """Generateur de rapport Google Docs - TOUS les POI"""
    
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
        creds_dir = BASE_DIR / 'credentials'
        creds_dir.mkdir(exist_ok=True)
        return creds_dir / 'credentials.json'
    
    def _get_token_path(self) -> Path:
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
        """Genere un document Google Docs avec TOUS les POI"""
        
        if not self.service:
            logger.error("Service Google non initialise")
            return None
        
        try:
            # 1. Creer le document
            doc_title = f"Analyse GPS - {data.get('analysis_id', 'unknown')}"
            
            doc = self.service.documents().create(body={'title': doc_title}).execute()
            doc_id = doc.get('documentId')
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            
            logger.info(f"Document Google cree: {doc_title}")
            logger.info(f"URL: {doc_url}")
            
            # 2. Construire le contenu
            requests = self._build_content(data)
            
            # 3. Mettre a jour le document
            if requests:
                # Diviser en lots de 100 pour eviter les erreurs
                for i in range(0, len(requests), 100):
                    batch = requests[i:i+100]
                    self.service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': batch}
                    ).execute()
            
            # 4. Sauvegarder l'URL
            url_file = output_dir / f'analysis_report_{data.get("analysis_id", "unknown")}_gdocs_url_.txt'
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
        """Construit le contenu du document - TOUS les POI"""
        requests = []
        summary = data.get('summary', {})
        track_info = summary.get('track_info', {})
        poi_search = summary.get('poi_search', {})
        poi_results = poi_search.get('results', {})
        pois = data.get('pois', [])
        
        current_index = 1
        
        # === TITRE ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "RAPPORT D'ANALYSE GPS\n\n"
            }
        })
        current_index += len("RAPPORT D'ANALYSE GPS\n\n")
        
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
        
        # === INFORMATIONS GENERALES ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "INFORMATIONS GENERALES\n"
            }
        })
        current_index += len("INFORMATIONS GENERALES\n")
        
        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len("INFORMATIONS GENERALES\n"),
                    'endIndex': current_index
                },
                'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                'fields': 'namedStyleType'
            }
        })
        
        info_text = (
            f"ID Analyse: {data.get('analysis_id', 'N/A')}\n"
            f"Fichier: {data.get('input_file', 'N/A')}\n"
            f"Date: {data.get('timestamp', 'N/A')}\n"
            f"Distance totale: {track_info.get('total_distance_km', 0)} km\n"
            f"Nombre de points: {track_info.get('total_points', 0)}\n\n"
        )
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': info_text
            }
        })
        current_index += len(info_text)
        
        # === RESUME ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "RESUME\n"
            }
        })
        current_index += len("RESUME\n")
        
        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len("RESUME\n"),
                    'endIndex': current_index
                },
                'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                'fields': 'namedStyleType'
            }
        })
        
        performance = summary.get('performance', {})
    
        # Dans la section RESUME
        resume_text = (
            f"Total POI: {poi_results.get('total_found', 0)}\n"
            f"POI nommes: {poi_results.get('named_count', 0)}\n"
            f"POI non nommes: {poi_results.get('unnamed_count', 0)}\n\n"
            f"--- PERFORMANCE ---\n"
            f"Temps total: {performance.get('total_duration_seconds', 0):.1f} s\n"
            f"Temps recherche POI: {performance.get('search_duration_seconds', 0):.1f} s\n"
            f"Temps calcul distances: {performance.get('distance_calculation_seconds', 0):.1f} s\n\n"
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
        if by_type and isinstance(by_type, dict):
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': "REPARTITION PAR TYPE\n"
                }
            })
            current_index += len("REPARTITION PAR TYPE\n")
            
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index - len("REPARTITION PAR TYPE\n"),
                        'endIndex': current_index
                    },
                    'paragraphStyle': {'namedStyleType': 'HEADING_2'},
                    'fields': 'namedStyleType'
                }
            })
            
            for poi_type, count in by_type.items():
                line = f"- {poi_type}: {count}\n"
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
                    'text': "\n"
                }
            })
            current_index += 1
        
        # === LISTE COMPLETE DES POI - TOUS SANS LIMITE ===
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': f"LISTE COMPLETE DES POI ({len(pois)})\n"
            }
        })
        current_index += len(f"LISTE COMPLETE DES POI ({len(pois)})\n")
        
        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index - len(f"LISTE COMPLETE DES POI ({len(pois)})\n"),
                    'endIndex': current_index
                },
                'paragraphStyle': {'namedStyleType': 'HEADING_1'},
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
            # TOUS les POI - AUCUNE LIMITE
            for i, poi in enumerate(pois, 1):
                name = self._safe_str(poi, 'name', 'Sans nom')
                poi_type = self._safe_str(poi, 'type', '')
                lat = self._safe_float(poi, 'lat', 0.0)
                lon = self._safe_float(poi, 'lon', 0.0)
                dist = self._safe_float(poi, 'distance', 0.0)
                address = self._safe_str(poi, 'address', '')
                phone = self._safe_str(poi, 'phone', '')
                website = self._safe_str(poi, 'website', '')
                hours = self._safe_str(poi, 'opening_hours', '')
                desc = self._safe_str(poi, 'description', '')
                gmaps = self._safe_str(poi, 'google_maps_url', '')
                overpass = self._safe_str(poi, 'overpass_url', '')
                
                # En-tete du POI
                header = f"{i}. {name}"
                if poi_type:
                    header += f" ({poi_type})"
                if dist > 0:
                    header += f" - {dist:.2f} km"
                header += "\n"
                
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': header
                    }
                })
                current_index += len(header)
                
                # Details
                details = []
                if lat != 0 or lon != 0:
                    details.append(f"  - Coordonnees: {lat:.6f}, {lon:.6f}")
                if address:
                    details.append(f"  - Adresse: {address}")
                if phone:
                    details.append(f"  - Telephone: {phone}")
                if website:
                    details.append(f"  - Site web: {website}")
                if hours:
                    details.append(f"  - Horaires: {hours}")
                if desc:
                    details.append(f"  - Description: {desc}")
                if gmaps:
                    details.append(f"  - Google Maps: {gmaps}")
                if overpass:
                    details.append(f"  - Overpass: {overpass}")
                
                if details:
                    detail_text = "\n".join(details) + "\n"
                    requests.append({
                        'insertText': {
                            'location': {'index': current_index},
                            'text': detail_text
                        }
                    })
                    current_index += len(detail_text)
                
                # Ligne de separation
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': "\n"
                    }
                })
                current_index += 1
            
            logger.info(f"Google Docs: {len(pois)} POI exportes")
        
        return requests