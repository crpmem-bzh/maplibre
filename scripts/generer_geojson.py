#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      GÉNÉRATEUR DE GEOJSON PAP-BZH                          ║
║                                                                              ║
║  Rassemble les données de délibération (CSV) + données spatiales (SHP)      ║
║  pour produire un GeoJSON prêt à afficher sur la carte MapLibre.            ║
║                                                                              ║
║  UTILISATION :                                                              ║
║      python3 generer_geojson.py [--verbose]                                ║
║                                                                              ║
║  FICHIERS D'ENTRÉE (dans le dossier data/) :                               ║
║      • delib.csv              → Délibération (Departement, Espece,          ║
║                                  Lib_zone, Zone, Groupe)                    ║
║      • zones-sanitaires.json  → Zones DGAL (convertis de SHP)               ║
║      • qm-bzh.json            → Quartiers maritimes (converti de SHP)       ║
║      • tellines-f.json        → Géométries Tellines manuelles               ║
║                                                                              ║
║  FICHIER DE SORTIE :                                                        ║
║      • PAP_BZH.geojson        → Prêt pour MapLibre, embarqué dans HTML     ║
║                                                                              ║
║  LOGIQUE PRINCIPALES :                                                      ║
║    → Cas A : Zone renseignée → jointure directe SHP sanitaire               ║
║    → Cas B : "Littoral du Morbihan" sans Zone → expansion 56.*              ║
║    → Cas C : Littoral générique → union quartiers maritimes                 ║
║    → Cas D : Tellines → 100% depuis tellines-f.json (CSV ignoré)            ║
║                                                                              ║
║  CLASSEMENT SANITAIRE :                                                      ║
║    • Groupe "-" → P (Pêche réglementée, hors classement DGAL)               ║
║    • Groupe "1/2/3" + Zone → classement GP1/GP2/GP3 du SHP                  ║
║                                                                              ║
║  AFFICHAGE :                                                                 ║
║    • Features "P" placées EN PREMIER → affichées sous les autres            ║
║    • Geométries simplifiées (tolerance=0.0003) pour perf MapLibre           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import csv
import json
import sys
import argparse
from pathlib import Path
from collections import Counter, defaultdict

# ════════════════════════════════════════════════════════════════════════════
# IMPORTS SPÉCIALISÉS
# ════════════════════════════════════════════════════════════════════════════
try:
    from shapely.geometry import shape, mapping, MultiPolygon, Polygon
    from shapely.ops import unary_union
    from shapely.validation import make_valid
except ImportError:
    sys.exit("❌ Module 'shapely' manquant.\n   Lance: pip install shapely")

# ════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DES CHEMINS
# ════════════════════════════════════════════════════════════════════════════
# Tous les chemins sont RELATIFS au dossier du script
# → facilite l'exécution depuis n'importe où (CI/CD, cron, etc)
BASE_DIR = Path(__file__).parent.parent  # Remonte au repo root
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = BASE_DIR / "scripts"

# Entrées
DELIB_CSV = DATA_DIR / "delib.csv"
SHP_SANITAIRE = DATA_DIR / "zones-sanitaires.geojson"
SHP_QM = DATA_DIR / "qm-bzh.geojson"
SHP_TELLINES_F = DATA_DIR / "tellines-f.geojson"

# Sortie
GEOJSON_OUT = DATA_DIR / "PAP_BZH.geojson"

# ════════════════════════════════════════════════════════════════════════════
# ZONES LITTORALES GÉNÉRIQUES
# ════════════════════════════════════════════════════════════════════════════
# Quand la délibération mentionne un "Littoral du Finistère" SANS Zone précise,
# on construit la géométrie en fusionnant les quartiers maritimes énumérés ici.
#
# CES ASSOCIATIONS SONT STABLES (définies par la délibération).
# Les updater ici si la délib change.
# ════════════════════════════════════════════════════════════════════════════
LITTORAUX_QM = {
    "Littoral du Finistère": [
        "AD", "DZ", "CM", "CC", "GV", "BR", "MX"
    ],
    "Littoral du Finistère (à l'exception des secteurs d'Audierne et de Douarnenez)": [
        "CM", "CC", "GV", "BR", "MX"
    ],
    "Littoral des côtes d'Armor": [
        "SB", "PL"
    ],
    "Littoral d'Ille & Vilaine": [
        "SM"
    ],
    "Secteur du Guilvinec": [
        "GV"
    ],
    "Secteur Nord Finistère": [
        "BR", "CM", "MX"
    ],
}


# ════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ════════════════════════════════════════════════════════════════════════════

def log(msg, level="INFO"):
    """Affichage formaté avec prefixe."""
    prefix = {"INFO": "✓", "WARN": "⚠", "ERROR": "❌", "STEP": "──"}[level]
    print(f"{prefix} {msg}")


def get_sanitaire(groupe, gp1, gp2, gp3):
    """
    Détermine le classement sanitaire selon le groupe d'espèces.
    
    Args:
        groupe (str): "1", "2", "3", ou "-" (hors classement)
        gp1, gp2, gp3 (str): Classements pour chaque groupe (A/B/C/I/EO/P ou NC)
    
    Returns:
        str: Classement ("A", "B", "C", "I", "EO", "NC", "P")
    """
    if groupe == '-':
        return 'P'  # Pêche réglementée, hors obligation DGAL
    if groupe == '1':
        return gp1 or 'NC'
    if groupe == '2':
        return gp2 or 'NC'
    if groupe == '3':
        return gp3 or 'NC'
    return 'NC'


def simplify_geom(geom, tolerance=0.0003):
    """
    Simplifie et normalise une géométrie en MultiPolygon.
    Élimine les artefacts topologiques et réduit la taille pour MapLibre.
    
    Args:
        geom (Shapely geometry): Géométrie d'entrée (peut être invalide)
        tolerance (float): Précision de simplification (0.0003 ≈ 30m)
    
    Returns:
        MultiPolygon or None: Géométrie nettoyée, ou None si vide
    """
    try:
        g = make_valid(geom.simplify(tolerance, preserve_topology=True))
        if g.is_empty:
            return None
        
        # Forcer MultiPolygon pour cohérence
        if g.geom_type == 'Polygon':
            g = MultiPolygon([g])
        elif g.geom_type != 'MultiPolygon':
            return None
        
        return g
    except Exception as e:
        log(f"Erreur simplification géométrie: {e}", "WARN")
        return None


# ════════════════════════════════════════════════════════════════════════════
# CHARGEMENT DES DONNÉES SOURCES
# ════════════════════════════════════════════════════════════════════════════

def load_delib_csv(filepath):
    """
    Charge le CSV de délibération.
    
    Format attendu:
        Departement,Espece,Lib_zone,Zone,Groupe
        29,"Coques et Palourdes","Baie de Douarnenez","29.07.061","2"
    
    Returns:
        list[dict]: Lignes avec clés Departement, Espece, Lib_zone, Zone, Groupe
    """
    if not filepath.exists():
        log(f"Fichier introuvable: {filepath}", "ERROR")
        return []
    
    rows = list(csv.DictReader(open(filepath, encoding='utf-8-sig')))
    log(f"Délibération: {len(rows)} lignes lues", "INFO")
    return rows


def load_geojson(filepath):
    """
    Charge un GeoJSON (SHP convertis en JSON).
    
    Returns:
        dict: {'type': 'FeatureCollection', 'features': [...]}
    """
    if not filepath.exists():
        log(f"Fichier introuvable: {filepath}", "WARN")
        return {'type': 'FeatureCollection', 'features': []}
    
    with open(filepath, encoding='utf-8') as f:
        return json.load(f)


def build_san_index(geojson_data):
    """
    Construit un index rapide pour lookup par Zone/CdZCY.
    
    Index = { CdZCY: {'geom': Shapely, 'GP1': 'A', 'GP2': 'B', 'GP3': 'C', 'Dep': 29}, ... }
    
    Args:
        geojson_data (dict): GeoJSON du SHP sanitaire
    
    Returns:
        dict: Index { zone_code → info_dict }
    """
    # Bretagne = codes 22, 29, 35, 56
    BZH_DEPS = {'22', '29', '35', '56'}
    
    index = {}
    for feature in geojson_data.get('features', []):
        props = feature.get('properties', {})
        dep_str = str(props.get('DepAdmiZCY', ''))
        
        # Filtrer hors-Bretagne
        if dep_str not in BZH_DEPS:
            continue
        
        try:
            # Convertir GeoJSON → Shapely geom
            geom = make_valid(shape(feature['geometry']))
            if geom.is_empty:
                continue
            
            # Créer entrée index
            zone_code = props.get('CdZCY', '')
            index[zone_code] = {
                'geom': geom,
                'GP1': props.get('ValClasGP1', 'NC'),
                'GP2': props.get('ValClasGP2', 'NC'),
                'GP3': props.get('ValClasGP3', 'NC'),
                'Dep': int(dep_str),
            }
        except Exception as e:
            log(f"Erreur parsing zone {props.get('CdZCY', '?')}: {e}", "WARN")
            continue
    
    log(f"Index sanitaire: {len(index)} zones Bretagne", "INFO")
    return index


def build_qm_unions(geojson_data):
    """
    Charge les quartiers maritimes et les préfusionne par code.
    Utile pour construire les géométries des "Littoraux génériques".
    
    Returns:
        dict: { code_QM → Shapely MultiPolygon }
    """
    # Grouper les polygones par code de quartier
    raw = defaultdict(list)
    for feature in geojson_data.get('features', []):
        props = feature.get('properties', {})
        code = props.get('QUARTIER', '')
        
        try:
            geom = make_valid(shape(feature['geometry']))
            if not geom.is_empty:
                raw[code].append(geom)
        except Exception as e:
            log(f"Erreur parsing QM {code}: {e}", "WARN")
            continue
    
    # Fusionner par quartier
    unions = {}
    for code, geoms in raw.items():
        unions[code] = make_valid(unary_union(geoms))
    
    log(f"Quartiers maritimes: {len(unions)} codes", "INFO")
    return unions


def build_littoraux_geom(qm_unions, littoraux_qm_map):
    """
    Construit les géométries des "Littoraux génériques" en fusionnant QM.
    
    Args:
        qm_unions (dict): { code_qm → geom }
        littoraux_qm_map (dict): { "Littoral X" → [codes_qm] }
    
    Returns:
        dict: { "Littoral X" → Shapely geom }
    """
    littoraux_geom = {}
    for lib, codes in littoraux_qm_map.items():
        geoms = [qm_unions[c] for c in codes if c in qm_unions]
        if geoms:
            littoraux_geom[lib] = make_valid(unary_union(geoms))
        else:
            littoraux_geom[lib] = None
    
    return littoraux_geom


def load_tellines_f(geojson_data):
    """
    Charge les géométries MANUELLES des Tellines depuis tellines-f.geojson.
    Ces géométries sont PRÉSERVÉES même si le CSV délibération est modifié.
    
    Returns:
        list[dict]: Features Tellines avec propriétés enrichies
    """
    out = []
    for feature in geojson_data.get('features', []):
        props = feature.get('properties', {})
        
        try:
            geom = make_valid(shape(feature['geometry']))
            if geom.is_empty:
                continue
            
            out.append({
                'Departement': int(props.get('Dprtmnt', 0)),
                'Espece': 'Tellines',
                'Lib_zone': props.get('Lib_zon', ''),
                'Zone': props.get('Zone', ''),
                'Groupe': props.get('Groupe', '-'),
                'Sanitaire': props.get('Sanitar', 'P'),
                'is_P': props.get('Sanitar', '') == 'P',
                'geom': geom,
            })
        except Exception as e:
            log(f"Erreur parsing Tellines: {e}", "WARN")
            continue
    
    log(f"Tellines: {len(out)} features préservées", "INFO")
    return out


# ════════════════════════════════════════════════════════════════════════════
# TRAITEMENT DE LA DÉLIBÉRATION
# ════════════════════════════════════════════════════════════════════════════

def process_delib(rows, san_index, littoraux_geom, zones_morbihan):
    """
    Traite chaque ligne de la délibération et produit les features GeoJSON.
    Gère 4 cas distincts selon Zone et Lib_zone.
    
    Args:
        rows (list): Lignes CSV
        san_index (dict): Index zones sanitaires
        littoraux_geom (dict): Géométries littoraux génériques
        zones_morbihan (dict): Sous-ensemble San index pour Morbihan (56)
    
    Returns:
        tuple: (list[feature_dict], list[warning_str])
    """
    features = []
    warns = []
    
    for row in rows:
        # Normaliser les champs
        dep = str(row.get('Departement', '')).strip()
        espece = row.get('Espece', '').strip()
        lib = row.get('Lib_zone', '').strip()
        zone = row.get('Zone', '').strip()
        groupe = row.get('Groupe', '').strip()
        
        # Les Tellines sont gérées séparément
        if espece == 'Tellines':
            continue
        
        # Base commune à tous les cas
        base = {
            'Departement': int(dep) if dep.isdigit() else dep,
            'Espece': espece,
            'Lib_zone': lib,
            'Groupe': groupe,
        }
        
        # ════════════════════════════════════════════════════════════════════
        # CAS A : Zone renseignée
        # ════════════════════════════════════════════════════════════════════
        # → Jointure directe sur l'index sanitaire (SHP DGAL)
        # Exemple: Zone="29.07.061", Groupe="2" → cherche GP2 pour cette zone
        # ════════════════════════════════════════════════════════════════════
        if zone:
            info = san_index.get(zone)
            if not info:
                warns.append(f"Zone introuvable: {zone} ({espece}, {lib})")
                continue
            
            san = get_sanitaire(groupe, info['GP1'], info['GP2'], info['GP3'])
            features.append({
                **base,
                'Zone': zone,
                'Sanitaire': san,
                'is_P': san == 'P',
                'geom': info['geom']
            })
        
        # ════════════════════════════════════════════════════════════════════
        # CAS B : "Littoral du Morbihan" SANS Zone
        # ════════════════════════════════════════════════════════════════════
        # → Création d'une feature pour CHAQUE zone 56.* du SHP
        # (expansion : 1 ligne CSV → N lignes GeoJSON)
        # ════════════════════════════════════════════════════════════════════
        elif lib == 'Littoral du Morbihan':
            if not zones_morbihan:
                warns.append(f"Pas de zones 56.* trouvées pour Morbihan expansion")
                continue
            
            for cdz, info in zones_morbihan.items():
                san = get_sanitaire(groupe, info['GP1'], info['GP2'], info['GP3'])
                features.append({
                    **base,
                    'Departement': 56,
                    'Zone': cdz,
                    'Sanitaire': san,
                    'is_P': san == 'P',
                    'geom': info['geom']
                })
        
        # ════════════════════════════════════════════════════════════════════
        # CAS C : Zone littorale générique (union quartiers maritimes)
        # ════════════════════════════════════════════════════════════════════
        # Exemple: Lib_zone="Littoral du Finistère" (pas de Zone)
        # → Géométrie = union QM ["AD","DZ","CM","CC","GV","BR","MX"]
        # ════════════════════════════════════════════════════════════════════
        elif lib in littoraux_geom:
            geom = littoraux_geom[lib]
            if geom is None:
                warns.append(f"Géométrie littorale vide: {lib}")
                continue
            
            # Les littoraux génériques ne sont pas classés DGAL → P
            san = 'P' if groupe == '-' else 'NC'
            features.append({
                **base,
                'Zone': lib,  # Utilise le libellé comme zone identifier
                'Sanitaire': san,
                'is_P': san == 'P',
                'geom': geom
            })
        
        else:
            warns.append(
                f"Cas non géré: zone='{zone}' lib='{lib}' espece='{espece}'"
            )
    
    log(f"Délibération traitée: {len(features)} features", "INFO")
    if warns:
        log(f"{len(warns)} avertissements:", "WARN")
        for w in warns:
            print(f"    - {w}")
    
    return features, warns


# ════════════════════════════════════════════════════════════════════════════
# EXPORT GEOJSON
# ════════════════════════════════════════════════════════════════════════════

def export_geojson(features, tellines, output_path):
    """
    Produit le fichier GeoJSON final.
    
    ORDRE IMPORTANT :
    • Features "P" EN PREMIER → MapLibre les affiche SOUS les autres
    • Puis les autres (A, B, C, I, EO, NC)
    
    Args:
        features (list): Features non-Tellines
        tellines (list): Features Tellines
        output_path (Path): Chemin de sortie
    """
    # Fusionner et trier (P d'abord)
    all_features = tellines + features
    sorted_feats = (
        [f for f in all_features if f.get('is_P')]
        + [f for f in all_features if not f.get('is_P')]
    )
    
    # Construire GeoJSON
    gj_features = []
    for f in sorted_feats:
        geom = simplify_geom(f['geom'])
        if geom is None:
            continue
        
        gj_features.append({
            'type': 'Feature',
            'geometry': mapping(geom),
            'properties': {
                'Departement': f['Departement'],
                'Espece': f['Espece'],
                'Lib_zone': f['Lib_zone'],
                'Zone': f['Zone'],
                'Groupe': f['Groupe'],
                'Sanitaire': f['Sanitaire'],
            }
        })
    
    gj = {
        'type': 'FeatureCollection',
        'features': gj_features
    }
    
    # Écrire
    out_str = json.dumps(gj, ensure_ascii=False, indent=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as fh:
        fh.write(out_str)
    
    # Stats
    size_kb = len(out_str) / 1024
    stats = Counter(f['properties']['Sanitaire'] for f in gj_features)
    
    log(f"Export: {len(gj_features)} features → {size_kb:.0f} KB", "INFO")
    log(f"Classements: {dict(stats)}", "INFO")
    log(f"Fichier: {output_path}", "INFO")


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main(verbose=False):
    """Orchestre l'ensemble du pipeline."""
    
    print("\n" + "="*80)
    print("GÉNÉRATEUR GEOJSON PAP-BZH")
    print("="*80 + "\n")
    
    # Étape 1 : Charger la délib
    log("Chargement délibération...", "STEP")
    rows_delib = load_delib_csv(DELIB_CSV)
    if not rows_delib:
        log("Aucune délibération trouvée. Abandon.", "ERROR")
        return False
    
    # Étape 2 : Charger le SHP sanitaire + construire index
    log("Chargement zones sanitaires DGAL...", "STEP")
    san_geojson = load_geojson(SHP_SANITAIRE)
    san_index = build_san_index(san_geojson)
    
    # Étape 3 : Charger quartiers maritimes + préfusionner
    log("Chargement quartiers maritimes...", "STEP")
    qm_geojson = load_geojson(SHP_QM)
    qm_unions = build_qm_unions(qm_geojson)
    littoraux_geom = build_littoraux_geom(qm_unions, LITTORAUX_QM)
    
    # Étape 4 : Charger Tellines manuelles (PRÉSERVÉES)
    log("Chargement Tellines (géométries manuelles)...", "STEP")
    tellines_geojson = load_geojson(SHP_TELLINES_F)
    tellines_f = load_tellines_f(tellines_geojson)
    
    # Étape 5 : Traiter la délib
    log("Traitement délibération...", "STEP")
    zones_morbihan = {
        cdz: info 
        for cdz, info in san_index.items() 
        if info['Dep'] == 56
    }
    features, warns = process_delib(rows_delib, san_index, littoraux_geom, zones_morbihan)
    
    # Étape 6 : Export GeoJSON final
    log("Export GeoJSON...", "STEP")
    export_geojson(features, tellines_f, GEOJSON_OUT)
    
    print("\n" + "="*80)
    log("✅ Génération réussie !", "INFO")
    print("="*80 + "\n")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Génère PAP_BZH.geojson")
    parser.add_argument('--verbose', action='store_true', help='Sortie détaillée')
    args = parser.parse_args()
    
    success = main(verbose=args.verbose)
    sys.exit(0 if success else 1)
