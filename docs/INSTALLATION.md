# 🚀 INSTALLATION INITIALE — PAP-BZH

## 📋 Prérequis

- **GitHub** : Repo et accès pour push
- **Python** 3.9+ (pour le script de génération local)
- **Git** (pour cloner et push)
- Éditeur de texte (VS Code, nano, etc.)
- **QGIS** (optionnel, pour éditer les Tellines ou convertir SHP)

---

## ✅ Étape 1 : Cloner le repo

```bash
# Cloner le repo GitHub
git clone https://github.com/<USERNAME>/maplibre.git
cd maplibre

# Vérifier la structure
ls -la
```

Expected:
```
.github/workflows/generate.yml
data/
  ├── delib.csv
  ├── zones-sanitaires.geojson
  ├── qm-bzh.geojson
  ├── tellines-f.geojson
  └── PAP_BZH.geojson (généré)
scripts/
  └── generer_geojson.py
docs/
index.html
README.md
.gitignore
```

---

## ✅ Étape 2 : Installer Python + dépendances

### Macbook / Linux
```bash
# Installer Python (si nécessaire)
# macOS
brew install python3

# Linux (Debian/Ubuntu)
sudo apt-get install python3 python3-pip

# Installer shapely
pip install shapely
```

### Windows
```bash
# Télécharger Python depuis https://www.python.org
# Cocher "Add Python to PATH" lors de l'installation

# Dans cmd:
pip install shapely
```

### Vérifier
```bash
python3 --version
python3 -c "import shapely; print(shapely.__version__)"
```

---

## ✅ Étape 3 : Convertir les fichiers SHP originaux en GeoJSON

Si tu as les fichiers `.shp` originaux de la DGAL, les convertir en GeoJSON pour GitHub.

### Option A : Avec QGIS (GUI)
```
1. Ouvrir QGIS
2. Fichier → Ouvrir → ZoneProdConchy_FXX.shp
3. Clic droit sur la couche → Exporter sous → GeoJSON
4. Sauvegarder dans data/zones-sanitaires.geojson
5. Répéter pour qm_bzh_s.shp → data/qm-bzh.geojson
6. Répéter pour tellines_f.shp → data/tellines-f.geojson
```

### Option B : Avec ogr2ogr (CLI)
```bash
# Installer GDAL (macOS)
brew install gdal

# Ou Linux
sudo apt-get install gdal-bin

# Convertir
ogr2ogr -f GeoJSON data/zones-sanitaires.geojson ZoneProdConchy_FXX.shp
ogr2ogr -f GeoJSON data/qm-bzh.geojson qm_bzh_s.shp
ogr2ogr -f GeoJSON data/tellines-f.geojson tellines_f.shp
```

### Vérifier
```bash
# Vérifier que les fichiers ont été générés
ls -lh data/*.geojson

# Vérifier qu'ils sont valides (JSON)
python3 -c "import json; json.load(open('data/zones-sanitaires.geojson'))"
```

---

## ✅ Étape 4 : Créer/vérifier delib.csv

Ton fichier `delib.csv` doit être en UTF-8, avec les colonnes:

```csv
Departement,Espece,Lib_zone,Zone,Groupe
29,"Coques et Palourdes","Baie de Douarnenez","29.07.061","2"
29,"Bulots","Littoral du Finistère","","1"
35,"Huîtres creuses","Anse de l'Arguenon","35.01.001","3"
```

**Format:**
- Encoding: **UTF-8** (pas de BOM)
- Delimiter: **virgule** (,)
- Guillemets: si espaces ou caractères spéciaux

### Tester localement
```bash
# Dans le dossier du repo
python3 scripts/generer_geojson.py

# Vérifier le résultat
ls -lh data/PAP_BZH.geojson
cat data/PAP_BZH.geojson | head -50
```

---

## ✅ Étape 5 : Configurer GitHub Pages

### Sur GitHub.com

1. Va dans **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: **main** / folder: **/ (root)**
4. Clique **Save**

### Attendre ~5 minutes
GitHub Pages génère l'URL: `https://<USERNAME>.github.io/maplibre/`

### Vérifier
```bash
# Dans le repo GitHub Actions tab
# Chercher le workflow "pages build and deployment"
# Il doit être ✅ Success
```

---

## ✅ Étape 6 : Premier push

```bash
# S'assurer qu'on est à jour
git pull origin main

# Ajouter tous les fichiers
git add -A

# Commit
git commit -m "🚀 Setup initial PAP-BZH"

# Push
git push origin main
```

**Le workflow GitHub Actions se lance automatiquement :**
1. Va dans Actions tab
2. Cherche "🗺️ Générer GeoJSON PAP"
3. Regarde les logs

Si ✅ Success:
- GeoJSON a été regénéré
- Changements sont commités
- GitHub Pages se met à jour

---

## 📝 Structurer delib.csv correctement

### Format CSV standard
```csv
Departement,Espece,Lib_zone,Zone,Groupe
```

### Cas A : Zone précise
```csv
29,"Coques et Palourdes","Baie de Douarnenez","29.07.061","2"
```
→ Jointure directe sur SHP sanitaire

### Cas B : Littoral du Morbihan (expansion)
```csv
56,"Huîtres creuses","Littoral du Morbihan","","3"
```
→ Crée une feature pour CHAQUE zone 56.* du SHP

### Cas C : Littoral générique
```csv
29,"Bulots","Littoral du Finistère","","1"
```
→ Géométrie = union QM ["AD","DZ","CM","CC","GV","BR","MX"]

### Cas D : Tellines (IGNORÉ)
```csv
35,"Tellines","Tellines Ille-et-Vilaine","","1"
```
→ Supprimer du CSV ou laisser : sera ignoré
→ Les vraies Tellines viennent de `tellines-f.geojson`

---

## 🔧 Troubleshooting installation

### ❌ "Python not found"
```bash
# Vérifier l'installation
which python3
python3 --version

# Ou utiliser python (Windows)
python --version
```

### ❌ "ImportError: No module named 'shapely'"
```bash
# Réinstaller
pip install --upgrade shapely

# Ou si pip ne fonctionne pas
python3 -m pip install shapely
```

### ❌ "CSV encoding error"
```bash
# Le CSV doit être en UTF-8 (sans BOM)
# Tester avec VS Code:
# 1. Ouvrir le fichier
# 2. Bas-droit: "UTF-8" (sans BOM)
# 3. Sauvegarder (Ctrl+S)
```

### ❌ "GeoJSON not found"
Vérifier que le SHP a été converti :
```bash
ls -la data/*.geojson
# Doit afficher 4 fichiers

# Vérifier qu'ils sont valides
python3 -c "import json; json.load(open('data/zones-sanitaires.geojson'))" && echo "OK"
```

### ❌ GitHub Actions échoue
1. Va dans Actions tab
2. Clique sur le workflow échoué
3. Regarde "🔧 Générer GeoJSON" pour les logs
4. Causes probables:
   - CSV mal encodé (UTF-8?)
   - Shapely non installé (mais Actions l'installe)
   - Zone inexistante dans le SHP sanitaire

---

## ✅ Vérifier que tout fonctionne

```bash
# 1. Clone + install
git clone <URL>
cd maplibre
pip install shapely

# 2. Générer le GeoJSON localement
python3 scripts/generer_geojson.py

# 3. Vérifier le GeoJSON
python3 -c "import json; gj = json.load(open('data/PAP_BZH.geojson')); print(f'Features: {len(gj[\"features\"])}')"

# 4. Push vers GitHub
git add -A
git commit -m "Test initial"
git push origin main

# 5. Checker Actions
# https://github.com/<USERNAME>/maplibre/actions
# Workflow doit être ✅ Success

# 6. Vérifier la carte
# https://<USERNAME>.github.io/maplibre/
```

---

## 📚 Ressources

- **Shapely docs** : https://shapely.readthedocs.io
- **GeoJSON spec** : https://geojson.org
- **MapLibre docs** : https://maplibre.org
- **GitHub Actions** : https://docs.github.com/en/actions
- **GitHub Pages** : https://pages.github.com

---

## 🎓 Prochaines étapes

Une fois l'installation réussie:

1. 📖 Lire [WORKFLOW.md](./WORKFLOW.md) pour comprendre les mises à jour
2. 🗺️ Lire [STRUCTURE.md](./STRUCTURE.md) pour l'architecture
3. 📝 Éditer `delib.csv` avec tes données réelles
4. 🚀 Push et laisser GitHub Actions faire le travail

Besoin d'aide? → Consulte les logs GitHub Actions ou les docs.

