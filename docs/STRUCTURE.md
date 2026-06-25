# 🏗️ STRUCTURE DU PROJET — PAP-BZH

## 📁 Arborescence

```
maplibre/
├── .github/
│   └── workflows/
│       └── generate.yml              ← Workflow GitHub Actions (auto-regen)
│
├── data/                             ← Données sources (CSV + GeoJSON)
│   ├── delib.csv                     ← Délibération (modifiée → regen auto)
│   ├── zones-sanitaires.geojson      ← SHP DGAL converti (changements rares)
│   ├── qm-bzh.geojson                ← Quartiers maritimes (fixe)
│   ├── tellines-f.geojson            ← Tellines manuelles (éditées dans QGIS)
│   └── PAP_BZH.geojson               ← SORTIE (généré par script Python)
│
├── scripts/
│   └── generer_geojson.py            ← Script Python (lance GitHub Actions)
│
├── docs/
│   ├── WORKFLOW.md                   ← Guide mise à jour pour utilisateurs
│   ├── STRUCTURE.md                  ← Ce fichier (architecture)
│   └── INSTALLATION.md               ← Setup initial
│
├── index.html                        ← Carte interactive (GitHub Pages)
├── README.md                         ← Entrée principale du repo
├── .gitignore                        ← Fichiers à ne pas versionner
└── LICENSE                           ← Licence du projet
```

---

## 🔄 Pipeline de données

```
                          ┌─────────────────────────────────────┐
                          │  Données sources modifiées          │
                          └──────────┬──────────────────────────┘
                                     │
                     ┌───────────────┼───────────────┐
                     │               │               │
                     ▼               ▼               ▼
              ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
              │ delib.csv   │ │tellines-f   │ │sanitaire.   │
              │(modifiable) │ │(éditée QGIS)│ │(DGAL update)│
              └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
                     │               │               │
                     │ Push vers      │ Push vers      │
                     │ main branch    │ main branch    │
                     │               │               │
                     └───────────────┼───────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │ GitHub Actions      │
                          │ Workflow détecte    │
                          │ le changement       │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │ Lancer script       │
                          │ generer_geojson.py │
                          └──────────┬──────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                │                    │                    │
                ▼                    ▼                    ▼
        ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
        │ Charger      │    │ Charger      │    │ Charger      │
        │ delib.csv    │    │ SHP sanitaire│    │ QM + Tellines│
        │              │    │ + construire │    │              │
        │              │    │ index        │    │              │
        └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
               │                   │                   │
               └───────────────────┼───────────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │ Traiter 4 cas:      │
                        │                     │
                        │ A) Zone précise     │
                        │ B) Morbihan expand  │
                        │ C) Littoral generic │
                        │ D) Tellines manuel  │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │ Simplifier geom     │
                        │ (MapLibre perf)     │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │ Exporter GeoJSON    │
                        │ PAP_BZH.geojson     │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │ Git auto-commit     │
                        │ + push to main      │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │ GitHub Pages        │
                        │ détecte changement  │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │ Carte mise à jour   │
                        │ (~30 secondes)      │
                        └─────────────────────┘
```

---

## 📊 Modèle de données

### 1. **delib.csv** (Délibération)

Format CSV simple. Définit quels timbres (espèces) sont autorisés où.

```csv
Departement,Espece,Lib_zone,Zone,Groupe
29,"Coques et Palourdes","Baie de Douarnenez","29.07.061","2"
29,"Bulots","Littoral du Finistère","","1"
56,"Télins Littoral du Morbihan","","","1"
35,"Huîtres creuses","Anse de l'Arguenon","35.01.001","3"
```

**Champs:**
- `Departement` (int): 22, 29, 35, ou 56
- `Espece` (str): Nom du timbre (ex: "Coques et Palourdes")
- `Lib_zone` (str): Nom humain de la zone (ex: "Baie de Douarnenez")
- `Zone` (str): Code CdZCY du SHP sanitaire DGAL, ou vide pour littoraux génériques
- `Groupe` (str): "1", "2", "3" (groupes d'espèces), ou "-" (hors classement → P)

### 2. **zones-sanitaires.geojson** (SHP DGAL)

Zones avec classements sanitaires du Ministère de l'Agriculture.
Convertis une fois du SHP original `ZoneProdConchy_FXX.shp`.

```geojson
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "MultiPolygon", "coordinates": [...] },
      "properties": {
        "CdZCY": "29.07.061",
        "DepAdmiZCY": "29",
        "ValClasGP1": "A",      ← Classement groupe 1
        "ValClasGP2": "B",      ← Classement groupe 2
        "ValClasGP3": "C"       ← Classement groupe 3
      }
    }
  ]
}
```

### 3. **qm-bzh.geojson** (Quartiers maritimes)

Découpe administrative des eaux bretonnes.
Permet de construire les géométries des littoraux génériques.

```geojson
{
  "type": "Feature",
  "geometry": { "type": "MultiPolygon", ... },
  "properties": {
    "QUARTIER": "GV"  ← Code du quartier (ex: "GV" pour Guilvinec)
  }
}
```

### 4. **tellines-f.geojson** (Tellines manuelles)

Géométries des zones de Tellines, éditées manuellement dans QGIS.
JAMAIS écrasées par le CSV (préservées lors de la génération).

```geojson
{
  "type": "Feature",
  "geometry": { "type": "MultiPolygon", ... },
  "properties": {
    "Dprtmnt": 35,
    "Lib_zon": "Anse de l'Arguenon",
    "Zone": "35.01.001",
    "Groupe": "1",
    "Sanitar": "B"    ← Classement (A/B/C/I/EO/P/NC)
  }
}
```

### 5. **PAP_BZH.geojson** (Sortie finale)

GeoJSON généré, embarqué dans `index.html` ou chargé dynamiquement.
Contient toutes les zones de pêche avec propriétés enrichies.

```geojson
{
  "type": "Feature",
  "geometry": { "type": "MultiPolygon", ... },
  "properties": {
    "Departement": 29,
    "Espece": "Coques et Palourdes",
    "Lib_zone": "Baie de Douarnenez",
    "Zone": "29.07.061",
    "Groupe": "2",
    "Sanitaire": "B"  ← Classement final
  }
}
```

---

## ⚙️ Logique du script generer_geojson.py

Le script traite **4 cas** distincts:

### **CAS A : Zone renseignée**
```
CSV: Zone="29.07.061", Groupe="2"
  ↓ Lookup dans zones-sanitaires.geojson
  ↓ Obtient GP2 (groupe 2) → "B"
  ↓ Crée feature avec classement "B"
```

### **CAS B : "Littoral du Morbihan" sans Zone**
```
CSV: Lib_zone="Littoral du Morbihan", Zone=""
  ↓ Expansion : cherche ALL zones 56.* dans SHP
  ↓ Crée N features (une par zone Morbihan)
  ↓ Chaque feature a son classement propre
```

### **CAS C : Littoral générique sans Zone**
```
CSV: Lib_zone="Littoral du Finistère", Zone=""
  ↓ Lookup dans LITTORAUX_QM["Littoral du Finistère"]
  ↓ Obtient codes: ["AD","DZ","CM","CC","GV","BR","MX"]
  ↓ Fusionne les QM correspondants
  ↓ Crée feature unique avec géométrie unifiée
```

### **CAS D : Tellines**
```
CSV: Espece="Tellines"
  ↓ IGNORÉ (skip)
  ↓ Les vraies Tellines viennent de tellines-f.geojson
  ↓ Ajoutées EN FIN (préservées)
```

---

## 🎯 Classements sanitaires

| Code | Signification | Groupe applicabilité |
|------|---------------|-------------------|
| **A** | Qualité excellente | Tous groupes |
| **B** | Qualité moyenne | Groupes 1, 2, 3 |
| **C** | Qualité médiocre | Groupes 1, 2, 3 |
| **I** | Interdit | Groupes 1, 2, 3 |
| **EO** | Autorisation requise | Groupes 1, 2, 3 |
| **NC** | Non classé | Défaut (pêche non autorisée) |
| **P** | Pêche réglementée | Groupe "-" uniquement |

---

## 🎨 Affichage MapLibre

### Ordre d'affichage
- **Features "P" EN PREMIER** dans le GeoJSON
  → MapLibre les affiche SOUS les autres
  → Visuellement moins important

### Couleurs
```javascript
A: #2ECC40   (vert)
B: #FFDC00   (jaune)
C: #FF851B   (orange)
I: #FF4136   (rouge)
EO: #0074D9  (bleu)
NC: #AAAAAA  (gris)
P: #EE82EE   (violet)
```

### Simplification géométrique
- Tolerance = 0.0003 (≈ 30 mètres)
- Élimine les micro-détails
- Réduit taille GeoJSON de ~40%
- Améliore perfs MapLibre

---

## 🔗 Relations entre fichiers

```
delib.csv
  │
  ├─ Lit "Zone" → JOIN zones-sanitaires.geojson
  │              (CAS A)
  │
  ├─ Lit "Lib_zone" → JOIN qm-bzh.geojson
  │                   (CAS C)
  │
  └─ Idem "Littoral du Morbihan" → EXPAND zones 56.*
                                   (CAS B)

tellines-f.geojson
  └─ Ajouté EN FIN (préservé)
     (CAS D)

═══════════════════════════════════════════════════════════

PAP_BZH.geojson (sortie)
  │
  ├─ Embarqué dans index.html (loading initial)
  │  ou chargé dynamiquement via fetch()
  │
  └─ Utilisé par MapLibre
     ├─ Couche fill (coloration par classement)
     ├─ Couche outline (contours)
     └─ Filtres + popup survol
```

---

## 📦 Dépendances Python

```bash
# Pour le script generer_geojson.py
pip install shapely
```

- **shapely** : Manipuler géométries (union, simplify, valid, etc)
- **json** : Parser/exporter GeoJSON (stdlib)
- **csv** : Lire délibération CSV (stdlib)
- **pathlib** : Gestion chemins (stdlib)

---

## 🌐 Dépendances JavaScript/HTML

```html
<!-- MapLibre GL JS v4.7.1 -->
<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>

<!-- SheetJS v0.18.5 (lecture Excel) -->
<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
```

---

## ✅ Checklist intégrité

Avant de déployer en production:

- [ ] Tous les fichiers SHP convertis en GeoJSON?
- [ ] Fichier `delib.csv` valide (UTF-8, colonnes OK)?
- [ ] Script Python testé localement?
- [ ] Workflow GitHub Actions configuré correctement?
- [ ] GitHub Pages enabled (Settings → Pages)?
- [ ] Fichiers sensibles dans `.gitignore` (credentials, backups)?
- [ ] `index.html` charge `PAP_BZH.geojson` depuis `/data/`?
- [ ] Tellines manuelles préservées lors du test?

---

## 🔐 Données sensibles

**N'PAS versionner :**
```
# .gitignore
*.tmp
*.bak
.DS_Store
node_modules/
```

