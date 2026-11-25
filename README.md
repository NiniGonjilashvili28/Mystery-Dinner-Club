# Mystery Dinner Club

Book a surprise dinner: you choose a city, a night, a mood and a budget, and we reserve a table at one
of our partner restaurants. Which one stays sealed until three hours before dinner.

**Live:** https://ngonjexstudents2026ui.z1.web.core.windows.net

The first visit after a quiet period can take up to a minute while Azure wakes the services and their
databases (see ADR 8). After that it is fast.

## How it is built

Two services, each with its own container and its own SQL Server database, and a static website:

| Part | What it does | Folder | Locally |
|---|---|---|---|
| Restaurants | Partner restaurants by city and mood, secret matching, table reservations, the details shown after the reveal | `services/restaurants` | http://localhost:8001 |
| Bookings | Accounts and login tokens, bookings (3 days ahead, from 30€, 1 to 8 guests), the 3-hour reveal, history, ratings | `services/bookings` | http://localhost:8002 |
| Website | Static pages that call both services from the browser | `ui` | http://localhost:8080 |

The website asks Restaurants for the list of cities. Everything else goes through Bookings, which calls
Restaurants over HTTP with a 3-second timeout to choose and reserve the restaurant and, after the reveal,
to show it. If Restaurants is down, new bookings are refused with a clear message and everything else
keeps working. `system.yaml` describes the whole system; each service has an `openapi.yaml`, and
`ADR.md` explains the decisions.

```
services/restaurants/   app.py, db.py (migration runner), logic.py, service.py, seed.py,
                        migrations/, tests/, openapi.yaml, Dockerfile
services/bookings/      app.py, db.py, logic.py, service.py, accounts.py, tokens.py,
                        restaurants_client.py, migrations/, tests/, openapi.yaml, Dockerfile
ui/                     index.html (welcome), book, booking, dinners, cities, login, signup,
                        app.js, style.css, config.js, images/
db/init.sql             creates both databases and one login per service (local only)
docker-compose.yml      the whole system locally
system.yaml             system description, checked against system.schema.json
tools/check_system.py   the CI check for system.yaml and the OpenAPI files
.github/workflows/      ci.yml (every push and pull request), cd.yml (every merge to main)
```

## Run everything locally

You need Docker Desktop. On an Apple Silicon Mac, turn on "Use Rosetta" in Docker's settings,
because SQL Server only exists for Intel.

```
git clone https://github.com/NiniGonjilashvili28/Mystery-Dinner-Club.git
cd Mystery-Dinner-Club
cp .env.example .env          # then put your own passwords and secret key in .env
docker compose up --build
```

Open http://localhost:8080. Compose starts SQL Server, runs `db/init.sql` once (`db-init`), then both
services (each applies its migrations and Restaurants loads its 150 sample restaurants) and nginx for
the website. `.env` is ignored by Git, so real passwords never reach the repository. Data is kept in
the `db-data` volume between runs; `docker compose down -v` deletes it.

To see the partial failure: `docker compose stop restaurants`, then try to book (you get a clear
message) and open My dinners (still works). `docker compose start restaurants` brings it back.

## Run a single service

With Docker, compose starts only what that service needs:

```
docker compose up --build restaurants      # SQL Server, db-init and Restaurants
```

Or with Python 3.12 on your machine, against the compose database:

```
docker compose up -d db db-init
set -a; source .env; set +a
cd services/restaurants
pip install -r requirements.txt
DATABASE_URL="mssql://restaurants_user:${RESTAURANTS_DB_PASSWORD}@localhost:1433/restaurants" python app.py
```

It listens on http://localhost:8000. Every setting comes from environment variables, all listed with
their defaults in `system.yaml`:

| Service | Variable | Default |
|---|---|---|
| both | `PORT` | `8000` |
| both | `DATABASE_URL` | none (secret) |
| both | `ALLOWED_ORIGIN` (CORS) | `http://localhost:8080` |
| both | `GIT_SHA` (shown by `/health`) | `dev` |
| Bookings | `SECRET_KEY` (signs login tokens) | none (secret) |
| Bookings | `RESTAURANTS_URL` | `http://restaurants:8000` |
| Bookings | `RESTAURANTS_TIMEOUT_S` | `3` |
| Bookings | `APP_TIMEZONE` | `Europe/Madrid` |

Both services answer `GET /health` with `{"status": "ok", "db": "ok", "version": "<git sha>"}`, or 503
if they cannot read and write their own database.

## Tests and coverage

The rule, client and API tests run without a database; the database and integration tests are
skipped unless `TEST_DATABASE_URL` points to an empty SQL Server database. To run everything for one
service:

```
docker compose up -d db
set -a; source .env; set +a
docker compose exec db /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C \
    -Q "CREATE DATABASE test_restaurants"
cd services/restaurants
pip install -r requirements-dev.txt
TEST_DATABASE_URL="mssql://sa:${MSSQL_SA_PASSWORD}@localhost:1433/test_restaurants" \
    pytest --cov=. --cov-report=term-missing --cov-fail-under=70
```

The same for Bookings with `test_bookings` and `services/bookings`. In CI both services reach about
95% coverage. Lint with `ruff check services`, and check the system description with
`pip install -r tools/requirements.txt` and `python tools/check_system.py`.

## How deployment works

- **CI** (`ci.yml`) runs on every push to a branch and every pull request: for each service it lints,
  starts a throwaway SQL Server, runs all tests with at least 70% coverage and builds the image; a
  third job checks `system.yaml` and both OpenAPI files.
- **CD** (`cd.yml`) runs on every merge to `main`: it runs the whole CI first, pushes both images to
  GitHub Container Registry tagged with the commit SHA, signs in to Azure with a managed identity
  (no password, OIDC), sets the database passwords as Container Apps secrets, switches both Container
  Apps to the new images, writes `ui/config.js` with the service addresses, uploads the website and
  fails unless both `/health` endpoints answer 200.
- Changes reach `main` only through pull requests, so CI always runs before CD. After the initial
  setup below, nothing on Azure is changed by hand.

## Initial Azure setup (done once)

These commands rebuild the same resources I created by following the course's deployment guide. Run
them in Azure Cloud Shell (Bash). Passwords are created randomly in the shell and only stored as
secrets; none of them is in this repository.

```
az account set --subscription "Azure for Students"
LOCATION=germanywestcentral          # allowed region where the free database offer works
USER_EMAIL=$(az account show --query user.name -o tsv)
PREFIX=$(echo "${USER_EMAIL%@*}" | tr . -)          # ngonj-exstudents2026
RG=rg-$PREFIX

# 1. Resource providers and the resource group
for p in Microsoft.App Microsoft.OperationalInsights Microsoft.Sql Microsoft.Storage Microsoft.ManagedIdentity; do
  az provider register --namespace $p
done
az group create --name $RG --location $LOCATION

# 2. Website: storage account with a static website
UI_STORAGE=$(echo "$PREFIX" | tr -d -)ui
az storage account create --name $UI_STORAGE --resource-group $RG --location $LOCATION --sku Standard_LRS --kind StorageV2
az storage blob service-properties update --account-name $UI_STORAGE --static-website --index-document index.html
UI_URL=$(az storage account show --name $UI_STORAGE --resource-group $RG --query primaryEndpoints.web -o tsv); UI_URL=${UI_URL%/}

# 3. SQL server, two free serverless databases, one user per database
SQL_SERVER=$PREFIX-sql
SQL_ADMIN_PASSWORD="Adm-$(openssl rand -hex 12)-9x"
az sql server create --name $SQL_SERVER --resource-group $RG --location $LOCATION --admin-user mdcadmin --admin-password "$SQL_ADMIN_PASSWORD"
az sql server firewall-rule create --resource-group $RG --server $SQL_SERVER --name AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
for s in restaurants bookings; do
  az sql db create --resource-group $RG --server $SQL_SERVER --name $PREFIX-$s-db \
    --edition GeneralPurpose --compute-model Serverless --family Gen5 --min-capacity 0.5 --capacity 1 \
    --backup-storage-redundancy Local --use-free-limit true --free-limit-exhaustion-behavior AutoPause
done
MY_IP=$(curl -s https://api.ipify.org)            # open the firewall for Cloud Shell only during setup
az sql server firewall-rule create --resource-group $RG --server $SQL_SERVER --name CloudShellSetup --start-ip-address $MY_IP --end-ip-address $MY_IP
mkdir -p ~/bin && curl -sL https://github.com/microsoft/go-sqlcmd/releases/download/v1.10.0/sqlcmd-linux-amd64.tar.bz2 | tar -xj -C ~/bin sqlcmd
RESTAURANTS_DB_PASSWORD="Rst-$(openssl rand -hex 12)-Q7"; BOOKINGS_DB_PASSWORD="Bkg-$(openssl rand -hex 12)-Q7"
for s in restaurants bookings; do
  if [ $s = restaurants ]; then PW=$RESTAURANTS_DB_PASSWORD; else PW=$BOOKINGS_DB_PASSWORD; fi
  ~/bin/sqlcmd -S tcp:$SQL_SERVER.database.windows.net,1433 -d $PREFIX-$s-db -U mdcadmin -P "$SQL_ADMIN_PASSWORD" -b \
    -Q "CREATE USER [${s}_user] WITH PASSWORD = '$PW'; ALTER ROLE db_ddladmin ADD MEMBER [${s}_user]; ALTER ROLE db_datareader ADD MEMBER [${s}_user]; ALTER ROLE db_datawriter ADD MEMBER [${s}_user];"
done
az sql server firewall-rule delete --resource-group $RG --server $SQL_SERVER --name CloudShellSetup
BOOKINGS_SECRET_KEY=$(openssl rand -hex 32)

# 4. Container Apps environment and the two apps (placeholder image until the first deploy)
az containerapp env create --name $PREFIX-env --resource-group $RG --location $LOCATION
az containerapp create --name $PREFIX-restaurants --resource-group $RG --environment $PREFIX-env \
  --image mcr.microsoft.com/k8se/quickstart:latest --ingress external --target-port 8000 \
  --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi \
  --secrets "database-url=mssql://restaurants_user:${RESTAURANTS_DB_PASSWORD}@${SQL_SERVER}.database.windows.net:1433/${PREFIX}-restaurants-db" \
  --env-vars "DATABASE_URL=secretref:database-url" "ALLOWED_ORIGIN=$UI_URL"
RESTAURANTS_URL=https://$(az containerapp show --name $PREFIX-restaurants --resource-group $RG --query properties.configuration.ingress.fqdn -o tsv)
az containerapp create --name $PREFIX-bookings --resource-group $RG --environment $PREFIX-env \
  --image mcr.microsoft.com/k8se/quickstart:latest --ingress external --target-port 8000 \
  --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi \
  --secrets "database-url=mssql://bookings_user:${BOOKINGS_DB_PASSWORD}@${SQL_SERVER}.database.windows.net:1433/${PREFIX}-bookings-db" "secret-key=${BOOKINGS_SECRET_KEY}" \
  --env-vars "DATABASE_URL=secretref:database-url" "SECRET_KEY=secretref:secret-key" "RESTAURANTS_URL=$RESTAURANTS_URL" "RESTAURANTS_TIMEOUT_S=3" "ALLOWED_ORIGIN=$UI_URL"

# 5. The pipeline's identity: Contributor on this resource group only, trusted only for main
az identity create --name $PREFIX-github --resource-group $RG --location $LOCATION
PRINCIPAL_ID=$(az identity show --name $PREFIX-github --resource-group $RG --query principalId -o tsv)
az role assignment create --assignee-object-id $PRINCIPAL_ID --assignee-principal-type ServicePrincipal \
  --role Contributor --scope $(az group show --name $RG --query id -o tsv)
REPO_JSON=$(curl -s https://api.github.com/repos/NiniGonjilashvili28/Mystery-Dinner-Club)
REPO_ID=$(echo "$REPO_JSON" | jq -r .id); OWNER_ID=$(echo "$REPO_JSON" | jq -r .owner.id)
az identity federated-credential create --name github-main --identity-name $PREFIX-github --resource-group $RG \
  --issuer https://token.actions.githubusercontent.com --audiences api://AzureADTokenExchange \
  --subject "repo:NiniGonjilashvili28/Mystery-Dinner-Club:ref:refs/heads/main"
az identity federated-credential create --name github-main-ids --identity-name $PREFIX-github --resource-group $RG \
  --issuer https://token.actions.githubusercontent.com --audiences api://AzureADTokenExchange \
  --subject "repo:NiniGonjilashvili28@${OWNER_ID}/Mystery-Dinner-Club@${REPO_ID}:ref:refs/heads/main"

# 6. Read access for the professors
for prof in amartini@faculty.ie.edu bserra@faculty.ie.edu; do
  az role assignment create --assignee $prof --role Reader --scope $(az group show --name $RG --query id -o tsv)
done
```

Then, in the repository's **Settings > Secrets and variables > Actions**:

- Secrets: `AZURE_CLIENT_ID` (the identity's client id), `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`,
  `RESTAURANTS_DB_PASSWORD`, `BOOKINGS_DB_PASSWORD`, `BOOKINGS_SECRET_KEY`.
- Variables: `PREFIX`, `RESOURCE_GROUP`, `UI_STORAGE`.

The first merge to `main` then deploys everything.

## Secrets and incidents

No password, key or connection string is stored in the repository, its workflows or its history:
local passwords live in `.env` (ignored by Git), CI creates a random throwaway database password in
each run, and Azure passwords are GitHub secrets passed to Container Apps as secrets. No secret has
leaked so far; if one does, it will be rotated and recorded here (what, when, what was done).

## AI disclosure

I used Claude (Anthropic) as an assistant throughout this project, for planning, code, infrastructure
files, tests and documentation. Every use is logged in `AI_USAGE.md` with what I asked, whether I kept,
changed or rejected the result, and an explanation in my own words. I tested and checked everything
myself and can explain every part of it.

## Known limits

- Restaurants are sample data, not real partners. Payment happens at the restaurant.
- Guests are not notified when their restaurant is revealed; they see it when they open the app
  (ADR 10).
- The first request after a quiet period is slow (scale to zero, ADR 8).
