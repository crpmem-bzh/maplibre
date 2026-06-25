
# 🔄 WORKFLOW DE MISE À JOUR — PAP-BZH

## 📋 Vue d'ensemble

Chaque modification de délibération ou de géométries déclenche automatiquement :
1. **Génération du GeoJSON** (script Python)
2. **Commit + Push** vers la branche `main`
3. **Déploiement** sur GitHub Pages (~30 secondes)

**Tu n'as pas besoin de lancer le script manuellement** — GitHub fait tout.

---

## 🔄 Scénarios de mise à jour

### 1️⃣ **La délibération change** (nouveau timbre, modification zone, etc.)

#### ✅ À faire :
```bash
# Éditer le fichier CSV localement
$ nano data/delib.csv
```

**Colonnes obligatoires :**
```
Departement,Espece,Lib_zone,Zone,Groupe
29,"Coques et Palourdes","Baie de Douarnenez","29.07.061","2"
56,"Bulots","Littoral du Morbihan","","1"
35,"Tellines","Tellines Ille-et-Vilaine","","1"
```

- **Departement** : 22, 29, 35, ou 56
- **Espece** : Nom exact du timbre (doit être identique partout pour les filtres)
- **Lib_zone** : Libellé humain de la zone
- **Zone** : Code CdZCY du SHP sanitaire (ex: `29.07.061`), ou vide si littoral générique
- **Groupe** : `1`, `2`, `3`, ou `-` (hors classement → P)

#### ✅ Push :
```bash
$ git add data/delib.csv
$ git commit -m "📝 Mise à jour délibération: ajout bulots baie de Douarnenez"
$ git push origin main
```

#### 🤖 GitHub Actions lance automatiquement :
- Lire le nouveau CSV
- Regénère PAP_BZH.geojson
- Commit et push le GeoJSON
- La carte se met à jour ~30 secondes après

---

### 2️⃣ **Les géométries des Tellines changent** (édition dans QGIS)

#### ✅ À faire :
```bash
# Modifier tellines-f.geojson dans QGIS (ou manuellement)
$ nano data/tellines-f.geojson

# Ou via QGIS :
# 1. Ouvrir QGIS
# 2. Charger data/tellines-f.geojson
# 3. Éditer les géométries
# 4. Exporter en GeoJSON → data/tellines-f.geojson
```

**Format attendu (GeoJSON) :**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "MultiPolygon", "coordinates": [...] },
      "properties": {
        "Dprtmnt": 35,
        "Lib_zon": "Anse de l'Arguenon",
        "Zone": "35.01.001",
        "Groupe": "1",
        "Sanitar": "B"
      }
    }
  ]
}
```

#### ✅ Push :
```bash
$ git add data/tellines-f.geojson
$ git commit -m "🐚 MAJ géométries tellines Ille-et-Vilaine (QGIS)"
$ git push origin main
```

Les Tellines manuelles sont **PRÉSERVÉES** lors de la génération — elles ne seront jamais écrasées par une modification du CSV.

---

### 3️⃣ **Le classement sanitaire change** (DGAL met à jour le SHP)

Quand la DGAL publie une nouvelle version du SHP sanitaire (`ZoneProdConchy_FXX.shp`) :

#### ✅ À faire :
```bash
# 1. Télécharger le SHP depuis https://www.atlas-sanitaire-coquillages.fr
# 2. Convertir en GeoJSON (QGIS ou ogr2ogr)
#    Format attendu :
#    - Champs: CdZCY, DepAdmiZCY, ValClasGP1, ValClasGP2, ValClasGP3
# 3. Remplacer data/zones-sanitaires.geojson

$ git add data/zones-sanitaires.geojson
$ git commit -m "🏥 MAJ classements sanitaires DGAL (v2024.06)"
$ git push origin main
```

---

### 4️⃣ **Les quartiers maritimes changent** (rare)

Si le SHP `qm_bzh_s.shp` est mis à jour par la région :

#### ✅ À faire :
```bash
# Convertir le SHP en GeoJSON (QGIS ou ogr2ogr)
# Format attendu : champ QUARTIER (code comme "AD", "GV", etc.)

$ git add data/qm-bzh.geojson
$ git commit -m "🌊 MAJ quartiers maritimes (source région)"
$ git push origin main
```

---

## 🤖 Vérifier l'exécution du workflow

### Sur GitHub.com :

1. Va sur ton repo → onglet **Actions**
2. Cherche le workflow **"🗺️ Générer GeoJSON PAP"**
3. Clique sur la dernière exécution
4. Regarde les logs :
   - ✅ **SUCCESS** = tout bon, carte à jour
   - ❌ **FAILED** = erreur (check les logs)

### Forcer une regénération manuelle :

1. Actions → "🗺️ Générer GeoJSON PAP"
2. **Run workflow** (bouton vert)
3. Sélectionne la branche `main`
4. Clique **"Run workflow"**

---

## 📝 Conventions de commit

Pour garder l'historique lisible, utilise ces préfixes :

| Préfixe | Signification | Exemple |
|---------|---------------|---------|
| 📝 | Délibération | `📝 Ajout Bulots secteur Guilvinec` |
| 🏥 | Classement sanitaire | `🏥 MAJ classements DGAL 2024` |
| 🐚 | Tellines (géométries) | `🐚 Correction géométries tellines 56` |
| 🌊 | Quartiers maritimes | `🌊 Update QM depuis SIG région` |
| 🔄 | Regénération auto | `🔄 Regénération GeoJSON PAP` |
| 📚 | Documentation | `📚 Update WORKFLOW.md` |

---

## ⚠️ Pièges courants

### ❌ Le workflow ne se déclenche pas ?

Vérifier :
- [ ] Fichier modifié = `data/delib.csv` ou `data/tellines-f.geojson`
- [ ] Branch = `main`
- [ ] Vous avez push sur la branche main (pas juste commit local)

### ❌ Le GeoJSON n'a pas été généré ?

1. Allez sur Actions → logs
2. Chercher l'erreur dans "🔧 Générer GeoJSON"
3. Causes probables :
   - CSV mal formaté (encoding UTF-8 ? colonnes manquantes ?)
   - Zone inexistante dans le SHP sanitaire
   - Shapely/Python erreur (contact Claude)

### ❌ Les Tellines ont disparu ?

**Ne l'inquiète pas** — c'est impossible 🔒

- Les Tellines sont chargées depuis `tellines-f.geojson`
- Le CSV délib est IGNORÉ pour elles
- Elles sont **ajoutées** après la génération du reste
- Modifie juste `tellines-f.geojson` pour les éditer

---

## 🚀 Déploiement sur GitHub Pages

Une fois les changements pushés :

1. GitHub Actions génère le GeoJSON (~10-30 secondes)
2. Le workflow commit/push le résultat
3. GitHub Pages détecte le changement automatiquement
4. La carte se met à jour (~30 secondes après)

**URL finale :** `https://<USERNAME>.github.io/maplibre/`

---

## 📞 Questions fréquentes

**Q: Et si je me trompe dans le CSV ?**
→ Corrige-le et push à nouveau. Le workflow se relance, pas de problème.

**Q: Puis-je éditer le GeoJSON directement ?**
→ Non, il est **régénéré automatiquement** à chaque push. Édite les sources (CSV ou GeoJSON tellines).

**Q: Puis-je utiliser un autre format que CSV pour la délib ?**
→ Actuellement non, mais on peut l'ajouter (Excel, Google Sheets, etc). Demande !

**Q: Combien de temps avant que la carte se mette à jour ?**
→ ~30-60 secondes après le push (workflow GitHub + GitHub Pages).

---

## 🔗 Ressources

- 📖 Docs DGAL : https://www.atlas-sanitaire-coquillages.fr
- 🗺️ QGIS (éditer SHP/GeoJSON) : https://qgis.org
- 🐚 Format GeoJSON : https://geojson.org
- 📊 CSV encoding : UTF-8 (sans BOM, with headers)

