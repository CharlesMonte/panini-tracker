# Déploiement Northflank

Objectif : héberger l'interface Next.js, l'API FastAPI et PostgreSQL sur Northflank, sans déployer Streamlit.

## Architecture

- Service `api` : FastAPI, Dockerfile `Dockerfile.api`, port privé `8000`.
- Service `web` : Next.js, Dockerfile `frontend/Dockerfile`, port public `3000`.
- Addon PostgreSQL : base de données Northflank.

Le front appelle l'API via `/api/backend/*`. En production Northflank, le build Next.js doit recevoir :

```text
NEXT_BACKEND_URL=http://api:8000
```

Le nom du service API doit donc être exactement `api`, ou il faudra adapter cette variable.

## Préparer la DB locale

Exporter la base locale actuelle :

```bash
mkdir -p backups
docker compose exec -T db pg_dump -U panini -d panini --no-owner --no-acl > backups/panini_northflank.sql
```

## Créer le projet Northflank

1. Créer un compte Northflank.
2. Ajouter une carte si Northflank le demande pour activer le Sandbox.
3. Créer un projet `panini-tracker`.
4. Connecter le repository GitHub du projet.

## Créer PostgreSQL

1. Dans le projet, créer un addon PostgreSQL.
2. Garder le plan gratuit/Sandbox si disponible.
3. Noter la variable `DATABASE_URL` générée par Northflank.

L'application accepte les deux formats :

```text
postgresql://...
postgresql+psycopg://...
```

## Restaurer la base

Depuis votre machine :

```bash
psql "DATABASE_URL_NORTHFLANK" < backups/panini_northflank.sql
```

Si `psql` n'est pas installé localement, utiliser un conteneur Docker temporaire :

```bash
docker run --rm -i postgres:16 psql "DATABASE_URL_NORTHFLANK" < backups/panini_northflank.sql
```

## Créer le service API

Créer un service depuis GitHub :

- Nom du service : `api`
- Type : service web / deployment service
- Build : Dockerfile
- Dockerfile path : `Dockerfile.api`
- Build context : racine du repo
- Port : `8000`
- Port public : désactivé si possible, sinon public uniquement le temps de tester
- Variables runtime :

```text
DATABASE_URL=<DATABASE_URL Northflank>
APP_ENV=production
SALE_PRICE=0.22
```

Healthcheck recommandé :

```text
/health
```

## Créer le service Web

Créer un deuxième service depuis GitHub :

- Nom du service : `web`
- Build : Dockerfile
- Dockerfile path : `frontend/Dockerfile`
- Build context : `frontend`
- Port : `3000`
- Port public : activé
- Variables build/runtime :

```text
NEXT_BACKEND_URL=http://api:8000
NODE_ENV=production
```

Ouvrir l'URL publique Northflank générée pour le service `web`.

## Vérifications

1. Ouvrir le front public `web`.
2. Vérifier le Dashboard.
3. Ajouter un sticker test.
4. Vérifier l'historique.
5. Exporter un Excel.
6. Si tout est OK, désactiver le port public de l'API s'il avait été activé pour debug.

## Sauvegardes

Faire un dump régulier depuis Northflank :

```bash
docker run --rm postgres:16 pg_dump "DATABASE_URL_NORTHFLANK" --no-owner --no-acl > backups/panini_$(date +%Y%m%d).sql
```

Conserver aussi des exports Excel depuis l'app.

## Limites

- Streamlit n'est pas déployé sur Northflank pour rester dans les deux services gratuits.
- L'app n'a pas encore d'authentification : avant de partager largement le lien, ajouter au minimum un mot de passe partagé.
- Les quotas Sandbox doivent être surveillés dans le dashboard Northflank.
