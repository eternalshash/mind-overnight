# ECE 473/573 Project 2: Persistent Marketplace

Project 2 replaces Project 1's in-memory marketplace with Postgres persistence,
adds account credit balances, and runs the service and database with Docker
Compose.

The supplied starter builds and runs. It can create, browse, and order listings,
and its data survives a marketplace-service restart. Two intentionally
incomplete sections discussed later are your Project 2 implementation tasks.
Do not redesign the API or rewrite the supplied SQL helpers.

## Ubuntu 24.04 VM Setup

This project requires an Ubuntu 24.04 LTS `amd64` VM and uses Go 1.26.

From the `ece573-prj02` directory root, provision a fresh VM with:

```bash
sudo ./setup_vm.sh
newgrp docker
```

The setup script installs and verifies Go 1.26.6, Git, `jq`,
Docker Engine, Buildx, and the Docker Compose plugin.
The `newgrp docker` command activates the new Docker-group
membership in the current terminal.

Verify the environment with:

```bash
go version
docker --version
docker buildx version
docker compose version
jq --version
```

## Quick Start

From the `ece573-prj02` project root, run:

```bash
./run_baseline.sh
```

The script resets the database, builds the marketplace-service image, starts
both Compose services, creates Alice and Bob, runs one list-to-browse-to-order flow,
restarts only the Go service, verifies that the sold listing remains sold,
and then stops both services. It is expected to pass before you complete either TODO.

Baseline responses are saved under `out/`. The Postgres volume is preserved, so
the data remains available after you restart the services with `./scripts/start.sh`.

## Individual Operations

The `scripts/` directory provides commands for composing your own tests:

- `./scripts/start.sh` builds the marketplace-service image and starts both
  Compose services. Existing database state is preserved.
- `./scripts/create-account.sh Alice 100` creates Alice with 100 credits. Its
  arguments are `account_id` and `starting_balance`.
- `./scripts/list.sh Alice "Used textbook" 25` creates a listing. Its arguments
  are `seller_id`, `title`, and `credit_cost`.
- `./scripts/browse.sh` returns all available listings.
- `./scripts/browse.sh Alice` returns only available listings created by Alice.
- `./scripts/order.sh listing-1 Bob` asks Bob to buy a listing. Use the
  `listing_id` returned by `list.sh`; generated IDs restart after a database
  reset but should not be assumed in tests.
- `./scripts/account.sh Bob` returns the balance, listings, purchases, and sales
  associated with Bob.
- `./scripts/stop.sh` stops and removes the Compose containers while retaining
  the PostgreSQL volume.
- `./scripts/reset.sh` stops the services and deletes the PostgreSQL volume. The
  next start creates an empty database from `database/schema.sql`.

## Source Structure

The source is separated by responsibility:

```text
docker-compose.yml                             service, database, network, and volume configuration
database/schema.sql                            tables, relationships, constraints, and timestamps
marketplace-service/Dockerfile                 multi-stage service image build
marketplace-service/main.go                    database configuration, startup, and route dispatch
marketplace-service/handlers.go                HTTP request and JSON response processing
marketplace-service/marketplace/store.go       connection, shared types, errors, and row scanners
marketplace-service/marketplace/accounts.go    account operations and read assembly
marketplace-service/marketplace/listings.go    listing operations
marketplace-service/marketplace/orders.go      checkout transaction
scripts/                                      individual lifecycle and API operations
```

Start with `main.go`. Its short route table shows the complete REST interface
without mixing in handler, business-rule, or SQL details.

## REST API

```text
POST /accounts
POST /listings
GET  /listings?seller_id={seller_id}
POST /orders
GET  /accounts/{account_id}
```

`POST /accounts` creates an account with a caller-supplied `starting_balance`.

`POST /listings` creates an available listing with a `seller_id`, `title`, and
positive `credit_cost`. The seller must reference an existing account.

`GET /listings` returns all available listings. The optional `seller_id` query
parameter restricts the result to one seller.

`POST /orders` asks a `buyer_id` to purchase a specified `listing_id`. A
successful checkout atomically transfers the listing cost from buyer to seller,
marks the listing sold, and records a completed order.

`GET /accounts/{account_id}` returns the account's balance, all listings it
created, orders it placed as a buyer, and orders it received as a seller.

## Implementation Task 1: Balance Transaction

Locate the first `TODO Project 2` in `CreateOrder`
(`marketplace-service/marketplace/orders.go`).
The starter already:

- begins a serializable transaction;
- locks and validates the listing;
- rejects a seller buying their own listing;
- locks the buyer and seller accounts in deterministic ID order;
- handles a nonexistent buyer;
- debits the buyer and credits the seller;
- marks the listing sold;
- inserts the completed order;
- commits on success and rolls back on error.

Between the supplied locked balance read and debit, return
`ErrInsufficientCredit` when the buyer balance is below the listing cost.

## Implementation Task 2: Account Assembly

Locate the second `TODO Project 2` in `GetAccount`
(`marketplace-service/marketplace/accounts.go`).
The starter creates the `Account`, obtains its balance, and assigns `AccountID`
and `Balance`. Four query helpers are provided below it:

```text
getBalance
getListingsBySeller
getOrdersByBuyer
getSalesBySeller
```

The starter calls `getBalance` as an example. Call each of the other three helpers,
return immediately on an error, assign the resulting activity fields, and
return the assembled `Account` value. Do not add a read transaction.

## Completed-Project Verification

After both TODOs are complete, run:

```bash
./acceptance.sh
```

The acceptance test creates its own accounts and discovers generated resource
IDs from API responses. It checks:

- account creation with explicit starting balances;
- seller-filtered listing browse;
- successful balance updates for seller and buyer;
- buyer orders and seller sales in account responses;
- insufficient-credit rejection without a debit or sale;
- repeat-order rejection without a second debit.

Responses are saved under `out/` for inspection and report evidence. On
success, the acceptance script stops both services and removes the Project 2
database volume.

## Useful Inspection and Troubleshooting Commands

- `docker compose ps` shows whether PostgreSQL is healthy and whether the
  marketplace service is running.
- `docker compose logs marketplace-service` displays service startup, request,
  and database errors.
- `docker compose logs postgres` displays database initialization and SQL
  errors.
- `docker compose exec postgres psql -U marketplace -d marketplace` opens an
  interactive SQL session in the running database container. Exit it with
  `\q`.

If port 8080 does not respond, first run `docker compose ps`, then inspect both
services' logs. If a Go source change does not appear in responses, run
`./scripts/start.sh`; its `--build` option rebuilds changed image layers and
reuses unchanged cached layers. If a schema change does not appear, run
`./scripts/reset.sh` before starting again.
