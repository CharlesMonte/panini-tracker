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
docker compose exec -T db pg_dump \
  -U panini \
  -d panini \
  --data-only \
  --no-owner \
  --no-acl \
  > backups/panini_northflank_data.sql
```

Ce dump contient uniquement les données. C'est volontaire : en base managée, il vaut mieux laisser l'application créer/maintenir les tables et éviter de supprimer/recréer le schéma `public`.

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

Avant une restauration complète, couper temporairement le service `api` dans Northflank. Cela évite que l'application écrive dans la base pendant la restauration.

### Première installation

1. Créer l'addon PostgreSQL.
2. Déployer et démarrer le service `api` une première fois.
3. Vérifier que l'API démarre : elle crée les tables si elles n'existent pas.
4. Couper temporairement le service `api`.
5. Restaurer les données avec la procédure ci-dessous.

### Mise à jour depuis un dump local

Vider les tables applicatives sans supprimer le schéma `public` :

```bash
docker run --rm -i postgres:16 psql "DATABASE_URL_NORTHFLANK" <<'SQL'
SET search_path TO public;
TRUNCATE TABLE
  trade_lines,
  trades,
  action_log,
  holdings,
  imports,
  stickers,
  people
RESTART IDENTITY CASCADE;
SQL
```

Restaurer ensuite les données :

```bash
docker run --rm -i postgres:16 psql "DATABASE_URL_NORTHFLANK" < backups/panini_northflank_data.sql
```

Relancer ensuite le service `api`.

Cette procédure est celle à utiliser pour mettre à jour Northflank depuis une sauvegarde locale. Elle évite les erreurs de contraintes existantes, ne dépend pas du droit `CREATE SCHEMA`, et conserve les permissions gérées par Northflank.

Si `psql` est installé localement, les mêmes commandes peuvent être exécutées avec `psql "DATABASE_URL_NORTHFLANK"` au lieu du conteneur Docker.

### Pourquoi ne pas faire `DROP SCHEMA public CASCADE`

Sur une base managée, l'utilisateur fourni dans `DATABASE_URL` n'est pas toujours propriétaire de la base et n'a pas forcément le droit `CREATE` au niveau database. Il peut avoir les droits nécessaires pour lire/écrire les tables applicatives sans avoir le droit de créer un schéma.

Il ne faut donc pas utiliser cette commande pour les mises à jour courantes :

```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

Si `public` est supprimé, l'API peut démarrer avec :

```text
psycopg.errors.InvalidSchemaName: no schema has been selected to create in
```

ou échouer avec :

```text
psycopg.errors.InsufficientPrivilege: permission denied for database ...
```

La bonne approche est de garder `public`, vider les tables avec `TRUNCATE`, puis restaurer un dump `--data-only`.

### Erreurs fréquentes de restauration

Si vous voyez des erreurs comme :

```text
ERROR: constraint "holdings_person_id_fkey" for relation "holdings" already exists
ERROR: constraint "trades_person_a_id_fkey" for relation "trades" already exists
```

c'est que le dump complet a été restauré par-dessus une base qui contenait déjà le schéma. Utiliser la procédure recommandée : dump `--data-only`, `TRUNCATE`, puis restauration des données.

Si le service `api` démarre avec :

```text
psycopg.errors.InvalidSchemaName: no schema has been selected to create in
LINE 2: CREATE TABLE people (
```

le schéma `public` existe mal, n'a pas les bons droits, ou n'est pas dans le `search_path`. Couper le service `api`, puis diagnostiquer :

```bash
docker run --rm -i postgres:16 psql "DATABASE_URL_NORTHFLANK" <<'SQL'
SET search_path TO public;
SHOW search_path;
SELECT current_schema();
SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'public';
SQL
```

Si `current_schema()` est vide ou si `public` n'apparaît pas, le schéma a probablement été supprimé. Le rôle applicatif peut ne pas avoir le droit de le recréer. Dans ce cas, recréer `public` depuis la console SQL Northflank ou avec l'utilisateur propriétaire/admin de l'addon :

```sql
CREATE SCHEMA public;
GRANT USAGE, CREATE ON SCHEMA public TO <utilisateur_api>;
ALTER ROLE <utilisateur_api> SET search_path TO public;
```

Le code API force aussi `search_path=public` côté connexion PostgreSQL, mais la base doit quand même contenir un schéma `public` utilisable.

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
