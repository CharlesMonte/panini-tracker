# Panini Tracker 2026

Application locale PostgreSQL + FastAPI + Next.js, avec fallback Streamlit, pour gérer une collection partagée de stickers Panini FIFA World Cup 2026.

## Stack

- Python 3.11
- FastAPI
- Next.js / TypeScript / Tailwind
- Streamlit fallback
- PostgreSQL
- SQLAlchemy 2
- pandas, openpyxl
- pytest
- Docker Compose

## Démarrage local

```bash
docker compose up --build
```

Puis ouvrir :

```text
http://localhost:3000
```

Services disponibles :

- Front Next.js : `http://localhost:3000`
- API FastAPI : `http://localhost:8000/docs`
- Streamlit fallback : `http://localhost:8501`
- PostgreSQL : `localhost:5432`

La base locale utilise :

- database : `panini`
- user : `panini`
- password : `panini`
- port : `5432`

## Importer l'Excel

Placez votre fichier dans `data/input/` ou utilisez le fichier fourni `source_excel.xlsx`.

Depuis le nouveau front :

1. Aller dans `Import / Export`.
2. Uploader le fichier ou laisser `source_excel.xlsx`.
3. Cliquer sur `Prévisualiser`.
4. Cliquer sur `Lancer l'import complet`.

Depuis le CLI Docker :

```bash
docker compose exec app python scripts/import_excel.py data/input/mon_fichier.xlsx
```

L'import détecte la feuille principale, les colonnes personnes, ignore les colonnes de calcul Excel et remplace les quantités existantes.

## Importer les noms de joueurs et équipes

Le fichier local `source_names.txt` est la source fixe pour enrichir les stickers avec labels, joueurs, équipes et flags foil.

```bash
docker compose exec app python scripts/import_source_names.py source_names.txt
```

Vous pouvez aussi lancer cet import depuis la page `Import / Export`, onglet `Noms stickers`.

## Exports

Depuis la page `Import / Export`, générez :

- CSV : matrice des quantités
- Excel multi-onglets :
  - `holdings_matrix`
  - `missing`
  - `duplicates`
  - `equivalent_trades`
  - `sale_candidates`
  - `history`

Les fichiers sont créés dans `data/exports/`.

## Tests

```bash
docker compose exec app pytest
```

Les tests couvrent la normalisation des codes, le parsing de `source_names.txt`, les échanges équivalents, les ventes possibles, l'import Excel minimal et les routes FastAPI principales.

Build front local :

```bash
cd frontend
npm install
npm run build
```

## Déploiement Northflank

Le déploiement recommandé pour partager l'app sans garder le Mac allumé est décrit dans [docs/NORTHFLANK.md](docs/NORTHFLANK.md).

Résumé :

- `api` FastAPI avec `Dockerfile.api`
- `web` Next.js avec `frontend/Dockerfile`
- PostgreSQL Northflank
- Streamlit non déployé en production

## Réinitialiser la base

```bash
docker compose exec app python scripts/reset_db.py
```

## Limites connues

- Pas d'authentification ni permissions.
- Pas de paiement réel.
- Les ventes et échanges groupés sont historisés; l'annulation automatique reste volontairement limitée aux actions simples et ventes annulables.
- Les noms de joueurs/équipes viennent du fichier local `source_names.txt`.
- Le front n'utilise pas de logos FIFA/Panini officiels; il reprend uniquement une direction visuelle inspirée album premium.
