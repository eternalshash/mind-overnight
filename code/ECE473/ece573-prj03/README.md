# ECE 473/573 Project 3: Marketplace Authentication and Authorization

Project 3 adds a login service to the persistent marketplace from Project 2
that issues Ed25519-signed JWTs after successfully authenticating users
with their passwords.
The updated marketplace service verifies the JWTs with the public key,
and then authorizes the RESTful requests.

The supplied starter performs registration, password hashing,
JWT issuance and verification, and the underlying marketplace operations.
It builds and runs with authentication disabled.
Two intentionally incomplete authorization sections discussed later
are your Project 3 tasks.
You are not asked to implement cryptography.

## Project 2 Release Boundary

This starter retains the unfinished Project 2 `accounts.go`
and `orders.go` files. It does not include their solutions.
If you completed Project 2 and want to carry over its account
and checkout behavior, you may copy your completed files
into this starter from the Project 3 root:

```bash
cp /path/to/your/ece573-prj02/marketplace-service/marketplace/accounts.go marketplace-service/marketplace/accounts.go
cp /path/to/your/ece573-prj02/marketplace-service/marketplace/orders.go marketplace-service/marketplace/orders.go
```

No Project 3 change belongs in those files.

## Ubuntu 24.04 VM Setup

This project requires an Ubuntu 24.04 LTS `amd64` VM and uses Go 1.26.

From the `ece573-prj03` directory root, provision a fresh VM with:

```bash
sudo ./setup_vm.sh
newgrp docker
```

The script installs and verifies Go 1.26.6, Git, `jq`, OpenSSL, Docker Engine,
Buildx, and the Docker Compose plugin.
The `newgrp docker` command activates the new Docker-group
membership in the current terminal.

Verify the environment with:

```bash
go version
docker --version
docker buildx version
docker compose version
jq --version
openssl version
```

## Quick Start

From the `ece573-prj03` project root, run:

```bash
./run_baseline.sh
```

The script resets the database and local signing key, starts
Postgres and both Go services, registers Alice and Bob, grants Bob credits,
and runs one list-to-browse-to-order flow with `AUTH_ENABLED=false`. It
restarts only marketplace and verifies that the listing remains sold. This
limited baseline passes before the Project 2 and Project 3 TODOs are
complete. Responses are saved under ignored `out/`. The script stops the
services but preserves the database volume and generated keys.

## Individual Operations

- `./scripts/rotate-secrets.sh` stops the services, rotates both signing
  keys and the admin password, and preserves the database volume. Run
  `./scripts/start.sh` afterward. Existing JWTs stop working.
- `./scripts/start.sh` checks that all three secret files exist, then builds
  and starts the Compose services without generating secrets.
  Set `AUTH_ENABLED=true` for protected marketplace routes; the default is
  `false`.
- `./scripts/create-account.sh Alice` creates a regular account with zero credits.
  It prompts for a password or reads one from stdin.
- `./scripts/login.sh Alice` prints a JSON response containing a JWT after
  reading Alice's password. It does not save the token to a file.
- `./scripts/admin-login.sh` prints an admin login response using the
  generated password.
- `./scripts/grant-credits.sh Bob 100` grants 100 credits to Bob. With
  authentication enabled, set `TOKEN` to an admin JWT.
- `./scripts/list.sh Alice "Used textbook" 25` creates a listing. With
  authentication enabled, set `TOKEN` to Alice's JWT.
- `./scripts/browse.sh` returns available listings; an optional seller ID
  filters the result. Browsing remains public.
- `./scripts/order.sh listing-1 Bob` places an order. Use the ID returned by
  `list.sh` and, with authentication enabled, Bob's JWT.
- `./scripts/account.sh Bob` reads Bob's balance and activity after
  completing Project 2 TODOs. With authentication enabled, use Bob's JWT.
  The acceptance and attack scripts do not require this to work.
- `./scripts/stop.sh` stops containers but preserves the database and keys.
- `./scripts/reset.sh` removes the database volume and regenerates keys and
  the admin password. Earlier JWTs cannot verify after key rotation.

Protected-route scripts read the JWT from `TOKEN`. Capture a login response
in a shell variable when you need its token; the login scripts do not store
JWTs. For example, starting with `AUTH_ENABLED=true`:

```bash
./scripts/reset.sh
AUTH_ENABLED=true ./scripts/start.sh
./scripts/create-account.sh Alice
./scripts/create-account.sh Bob
ADMIN_TOKEN="$(./scripts/admin-login.sh | jq -er .access_token)"
TOKEN="$ADMIN_TOKEN" ./scripts/grant-credits.sh Bob 100
ALICE_TOKEN="$(./scripts/login.sh Alice | jq -er .access_token)"
TOKEN="$ALICE_TOKEN" ./scripts/list.sh Alice "Book" 25
```

## Source Structure

```text
docker-compose.yml                             services, environment, keys, and database volume
Dockerfile                                     separate login and marketplace build targets
database/schema.sql                            persistent accounts, credentials, listings, orders
auth/jwt.go                                    supplied token issuance and verification
login-service/main.go                          login routes and startup
login-service/handlers.go                      registration and login HTTP handling
login-service/login_service.go                 registration and login implementations
marketplace-service/main.go                    feature flag and marketplace routes
marketplace-service/authorization.go           authorization wrapper and helpers
marketplace-service/handlers.go                marketplace HTTP and JSON handling
marketplace-service/marketplace/               marketplace implementations
scripts/                                       lifecycle and API operations
```

Start with `marketplace-service/main.go`. Its route table shows protected and
public operations and where the TODOs belong.

## REST API and Access Rules

| Service | Route | Access when authentication is enabled |
| --- | --- | --- |
| Login | `POST /accounts` | Register a regular account; no token |
| Login | `POST /login` | Check a password and issue a JWT; no token |
| Marketplace | `GET /listings?seller_id={seller_id}` | Public browse |
| Marketplace | `POST /listings` | User token with subject matching `seller_id` |
| Marketplace | `POST /orders` | User token with subject matching `buyer_id` |
| Marketplace | `GET /accounts/{account_id}` | Token with subject matching path ID |
| Marketplace | `POST /accounts/{account_id}/credits` | Admin token; regular-user target |

Registration accepts `account_id` and a password of at least eight Unicode
characters, always assigns role `user`, and starts the balance at zero.
`POST /login` returns a Bearer JWT containing `sub`, `role`, `iss`, `aud`,
`iat`, and `exp` claims. Tokens expire after 30 minutes.
The private key is mounted only in login; marketplace receives the public key.

With `AUTH_ENABLED=false`, marketplace does not require tokens and logs a
development-only warning.
With `AUTH_ENABLED=true`, regular users can list and buy for themselves;
the admin can grant positive credits to regular accounts but cannot list or buy.

## Implementation Task 1: Protected Route Registration

Locate `TODO Project 3` in `marketplace-service/main.go`. Use the protected
`POST /listings` registration as the pattern and add wrappers for:

```text
POST /orders                        matchBody("buyer_id"), allowRole("user")
GET  /accounts/{account_id}         matchPath("account_id"), allowAny()
POST /accounts/{account_id}/credits matchAny(), allowRole("admin")
```

An admin can grant credits to the account named in the path without having
that account ID. The supplied store still rejects a non-user target. Leave
public browse outside the authorization wrapper. Until these three routes
are registered, requests to them with authentication enabled have no
matching route.

## Implementation Task 2: Authorization Wrapper

Locate `TODO Project 3` in `requireAuthorization`
(`marketplace-service/authorization.go`). The starter already parses the
Bearer header, verifies the JWT, and supplies `matchBody`, `matchPath`,
`matchAny`, `allowRole`, and `allowAny` filters.

Call the selected ID filter with the verified subject. Return HTTP 400 if it
reports an invalid identity field. If the ID matches and the role filter
allows the verified role, call the wrapped handler and return. Otherwise
return HTTP 403. A missing or invalid token already returns HTTP 401. Keep
this check in the shared wrapper.

## Completed-Project Verification

After finishing both Project 3 TODOs, run:

```bash
./acceptance.sh
./attack.sh
```

`acceptance.sh` checks the successful registration, credit-grant, listing,
browse, and order flow. Its responses are saved under `out/`.
`attack.sh` numbers ten rejection checks covering passwords, tokens, identity,
roles, and invalid credit targets. Its responses are saved under `out/attack/`.
Each script resets the database and signing keys, then stops services on success.

## Useful Inspection and Troubleshooting Commands

- `docker compose ps` shows Postgres health and service states.
- `docker compose logs login-service` shows registration and login errors.
- `docker compose logs marketplace-service` shows route and request errors.
- `docker compose logs postgres` shows database initialization errors.
- `docker compose exec postgres psql -U marketplace -d marketplace` opens
  the database; exit with `\q`.

If a protected route returns HTTP 404, inspect its registration in
`marketplace-service/main.go`. If it returns HTTP 401, check the Bearer token
and whether `reset.sh` rotated the signing key. If a Go change does not
appear in responses, run `./scripts/start.sh` to rebuild the images. If a
schema change does not appear, reset the database before starting again.