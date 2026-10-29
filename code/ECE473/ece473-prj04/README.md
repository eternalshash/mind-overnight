# ECE 473/573 Project 4: Distributed Database Systems

Project 4 adds a three-node Cassandra cluster to the shopping marketplace.
Postgres remains authoritative for credentials, balances, listings, and orders.
After a listing or order commits in Postgres, marketplace copies it to
Cassandra views used by the GET routes.

The starter provides all scripts and source code including
the Cassandra schema, projections, and account queries.
Project 4 focuses on comparing read and write consistency while requesting
two or three Cassandra nodes under a fixed replication factor of three.
The baseline checks a completed order, the Cassandra account and listing
views, and a marketplace restart.
The experiment script is used for the five experiments discussed later.

## Carry-forward boundary

This project no longer depends on your completed Project 2.
Optionally, you may incorporate your updates from Project 3
by editing the Project 3 TODO sections in
`marketplace-service/main.go` and
`marketplace-service/authorization.go`.
The provided workflows use `AUTH_ENABLED=false`
that permits access to account and history without authorization.

## Ubuntu 24.04 VM Setup

This project requires an Ubuntu 24.04 LTS `amd64` VM and uses Go 1.26.

From the `ece573-prj04` directory root, provision a fresh VM with:

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

## Quick start

From the `ece573-prj04` project root, run:

```bash
./run_baseline.sh
```

The baseline resets project database volumes and local signing keys, starts
services, exercises a marketplace flow, saves responses under ignored `out/`,
and stops services on success. It checks checkout and restart persistence,
buyer and seller account views, sold-listing status, browse removal, balances,
and a date-range read.

## Individual Operations

Project 4 keeps most of the Project 3 scripts.
Please refer to Project 3 for details on enabling authentication and authorization.

- `./scripts/reset.sh` removes the database volumes and regenerates keys and
  the admin password.
- `./scripts/start.sh` builds and starts the Compose services.
- `./scripts/create-account.sh Alice` creates a regular account with zero credits.
  It prompts for a password or reads one from stdin.
- `./scripts/login.sh Alice` prints a JSON response containing a JWT after
  reading Alice's password. It does not save the token to a file.
- `./scripts/admin-login.sh` prints an admin login response using the
  generated password.
- `./scripts/grant-credits.sh Bob 100` grants 100 credits to Bob.
- `./scripts/list.sh Alice "Used textbook" 25` creates a listing.
- `./scripts/browse.sh` returns available listings; an optional seller ID
  filters the result. Browsing remains public.
- `./scripts/order.sh listing-1 Bob` places an order.
  Use the ID returned by `list.sh`.
- `./scripts/account.sh Bob 2000-01-01 2000-01-02`
  reads Bob's balance and activity, optionally within a time range.
- `./scripts/stop.sh` stops containers but preserves the database and keys.

## Source Structure

```text
docker-compose.yml                       Postgres, login, marketplace, Cassandra ×3
database/schema.sql                      authoritative account/listing/order tables
login-service/                           registration, login, and admin bootstrap
auth/                                    copied JWT helpers
marketplace-service/main.go              startup and route registrations
marketplace-service/authorization.go     optional Project 3 authorization TODO
marketplace-service/handlers.go          listing, checkout, and account HTTP handlers
marketplace-service/model/               listing and order types shared by both stores
marketplace-service/history/             Cassandra tables, writes, and reads
marketplace-service/marketplace/         Postgres marketplace logic
scripts/                                 lifecycle and request helpers
```

## REST API

Project 4 keeps the Project 3 routes and response shapes: `POST /listings`,
`GET /listings?seller_id=...`, `POST /orders`, `GET /accounts/{account_id}`,
and `POST /accounts/{account_id}/credits`. Login owns `POST /accounts` and
`POST /login`.

`GET /accounts/{account_id}` returns the current Postgres balance together
with Cassandra-backed `listings`, `orders`, and `sales` arrays. With no query
parameters it returns all account activity. Optional `from` and `to` values
filter orders and sales by inclusive UTC order dates; they do not filter
listings. Either bound may be omitted. Invalid dates or a reversed range
return HTTP 400. Cassandra read failures return HTTP 503.

## Consistency Experiment

Each run of `run_experiment.sh` resets the Postgres and Cassandra volumes,
requests two or three Cassandra nodes, and waits for marketplace service readiness. Marketplace creates the Cassandra schema before serving requests,
but the third node may still be joining.
The run creates five listings and places five orders.
Its final request is `GET /accounts/Alice`;
only that request's HTTP status and formatted JSON body are saved under
`out/experiment-write-*-read-*-nodes-*.txt`.
The first consistency level is for writes, and the second is for reads.

Run the cases separately and refer to the table below for a brief summary.

```bash
./run_experiment.sh QUORUM QUORUM 3
./run_experiment.sh QUORUM QUORUM 2
./run_experiment.sh ONE ONE 2
./run_experiment.sh ALL ONE 2
./run_experiment.sh ONE ALL 2
```

| Nodes requested | Write/read | What to examine |
| --- | --- | --- |
| 3 | `QUORUM/QUORUM` | Reference run: locate the response, node status, Postgres rows, and logs. |
| 2 | `QUORUM/QUORUM` | Check whether two nodes satisfy both quorums. |
| 2 | `ONE/ONE` | Compare the observed result with what this setting guarantees. |
| 2 | `ALL/ONE` | Projection writes cannot satisfy `ALL`; compare Postgres orders with Cassandra views and projection-error logs. |
| 2 | `ONE/ALL` | Writes can succeed, but Cassandra reads need three replicas and return HTTP 503. |

Each run leaves the services running so you can inspect node status, logs,
Postgres rows, or make additional requests.

## Useful Inspection and Troubleshooting Commands

- `docker compose ps` shows Postgres health and service states.
- `docker compose logs marketplace-service` shows route and request errors.
- `docker compose logs cassandra-1` shows Cassandra initialization errors.
- `docker compose exec cassandra-1 nodetool status` shows Cassandra cluster status.
- `docker compose exec cassandra-1 cqlsh` opens the Cassandra database.

