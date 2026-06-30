#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de configuration pour Google Docs API
Permet de generer les credentials necessaires pour l'utilisation du generateur Google Docs
"""

import json
import sys
from pathlib import Path

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import BASE_DIR

def create_credentials_file():
    """Cree le fichier credentials.json avec les instructions"""
    
    creds_dir = BASE_DIR / 'credentials'
    creds_dir.mkdir(exist_ok=True)
    
    creds_file = creds_dir / 'credentials.json'
    
    print("=" * 60)
    print("Configuration Google Docs API")
    print("=" * 60)
    print()
    print("Pour utiliser le generateur Google Docs, vous devez:")
    print()
    print("1. Aller sur Google Cloud Console: https://console.cloud.google.com/")
    print("2. Creer un projet ou en selectionner un existant")
    print("3. Activer l'API Google Docs et Google Drive")
    print("4. Creer des credentials de type 'Application de bureau'")
    print("5. Telecharger le fichier JSON")
    print("6. Renommer le fichier en 'credentials.json'")
    print("7. Le placer dans le dossier: " + str(creds_dir))
    print()
    print("=" * 60)
    
    # Creer un fichier d'exemple
    if not creds_file.exists():
        example = {
            "installed": {
                "client_id": "VOTRE_CLIENT_ID",
                "project_id": "VOTRE_PROJECT_ID",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "VOTRE_CLIENT_SECRET",
                "redirect_uris": ["http://localhost"]
            }
        }
        
        with open(creds_file, 'w') as f:
            json.dump(example, f, indent=2)
        
        print(f"Fichier d'exemple cree: {creds_file}")
        print("Modifiez-le avec vos credentials Google")
    else:
        print(f"Fichier credentials.json existe deja: {creds_file}")

def test_connection():
    """Teste la connexion Google Docs"""
    
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        print("Erreur: Bibliotheques Google manquantes")
        print("Installez: pip install google-api-python-client google-auth-oauthlib")
        return False
    
    creds_dir = BASE_DIR / 'credentials'
    token_file = creds_dir / 'token_gdocs.json'
    
    if not token_file.exists():
        print("Token non trouve. Lancez d'abord une analyse avec le generateur gdocs")
        return False
    
    try:
        with open(token_file, 'r') as f:
            creds_data = json.load(f)
            creds = Credentials.from_authorized_user_info(creds_data)
        
        service = build('docs', 'v1', credentials=creds)
        # Test simple: recuperer les infos du compte
        drive_service = build('drive', 'v3', credentials=creds)
        about = drive_service.about().get(fields='user').execute()
        
        email = about.get('user', {}).get('emailAddress', 'inconnu')
        print(f"Connexion Google Docs reussie!")
        print(f"Compte: {email}")
        return True
        
    except Exception as e:
        print(f"Erreur connexion: {e}")
        return False

def main():
    print("=" * 60)
    print("Configuration Google Docs API")
    print("=" * 60)
    print()
    
    print("1. Configurer les credentials")
    create_credentials_file()
    print()
    
    print("2. Tester la connexion")
    if test_connection():
        print("✅ Connexion OK")
    else:
        print("❌ Connexion KO")
    print()
    
    print("Pour utiliser le generateur Google Docs:")
    print("  python main.py track.gpx --report-formats gdocs")
    print()

if __name__ == '__main__':
    main()