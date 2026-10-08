# ECE 473/573 Project 1: Containerized Marketplace

Project 1 is an environment-readiness and testing project.
You will run a small Go marketplace service in Docker,
and design tests that cover both normal and failure cases.
You do not need to modify the supplied service source code.

## Ubuntu 24.04 VM Setup

This project requires an Ubuntu 24.04 LTS `amd64` VM
and uses Go 1.26.

From the parent `ece573-prj01` directory, provision a fresh VM with:

```bash
sudo ./setup_vm.sh
newgrp docker
```

The setup script installs and verifies Go 1.26.6, Git,
Docker Engine, Buildx, and the Docker Compose plugin.
The `newgrp docker` command activates the new Docker-group
membership in the current terminal.

Verify the environment with:

```bash
go version
docker --version
docker buildx version
docker compose version
```

## Quick Start

From the `ece573-prj01` project root, run:

```bash
./run_baseline.sh
```

The script calls the individual operation scripts,
runs one list-to-browse-to-order flow,
writes the responses into `out/`, and stops the container.
Before running additional tests,
students should run `./scripts/start.sh`.

## Individual Operations

The `scripts/` directory provides commands for composing your own tests:

- `./scripts/build.sh` builds the `ece573-prj01` image from `marketplace-service/`. Run it after changing the service source or Dockerfile, which is usually not necessary after running
`./run_baseline.sh`.
- `./scripts/start.sh` replaces any existing `ece573-prj01` container and starts a fresh container from the current image.
- `./scripts/list.sh Alice "Used textbook" 25` creates a listing. Its arguments are `seller_id`, `title`, and `credit_cost`.
- `./scripts/browse.sh` returns the available listings.
- `./scripts/order.sh listing-1 Bob` orders a listing. Its arguments are `listing_id` and `buyer_id`.
- `./scripts/stop.sh` removes the running `ece573-prj01` container.

## Useful Inspection Commands

- `docker ps --filter name=ece573-prj01` shows the project container and whether it is running.
- `docker logs ece573-prj01` displays the container's application output for troubleshooting.