# ECE 473/573 Project 6: Distributed Message Queues

Project 6 adds Kafka to the Project 5 shopping marketplace. The marketplace API
publishes listing and order commands and returns HTTP 202 after Kafka acknowledges
them. Workers consume the commands, commit business results to Postgres, and
attempt to update the Cassandra read views. The API and workers run as separate
Kubernetes Deployments.

## Ubuntu 24.04 VM Setup

This project requires an Ubuntu 24.04 LTS `amd64` VM and uses Go 1.26.
Use a fresh VM because the cluster needs ports 8080 and 8081.

From the `ece573-prj06` repository root, provision the VM with:

```bash
sudo ./setup_vm.sh
newgrp docker
```

The script installs and verifies Go 1.26.6, Git, `jq`, OpenSSL, Python 3,
Docker Engine, Buildx, `kind`, and `kubectl`. It also sets the host inotify
instance limit needed by the six kind nodes. `newgrp docker` activates the
Docker-group membership in the current terminal.

Verify the environment with:

```bash
go version
docker --version
docker buildx version
kind version
kubectl version --client
python3 --version
```

## Quick Start

From the `ece573-prj06` project root, run:

```bash
./create_cluster.sh
./deploy_apps.sh
./run_baseline.sh
```

`create_cluster.sh` creates one control-plane node and five worker nodes, loads
the database and Kafka images, deploys Postgres, Cassandra, and Kafka, and
creates the `marketplace.commands` topic. `deploy_apps.sh` builds and loads the
application images and waits for the Deployments. Both scripts select the
Project 6 `kubectl` context.

| Component | Pods | Role |
| --- | ---: | --- |
| Marketplace services | 2 | Accepts requests at `http://127.0.0.1:8080` |
| Login service | 1 | Serves account registration and login at `http://127.0.0.1:8081` |
| Marketplace workers | 2 | Consume one Kafka consumer group |
| Postgres | 1 | Stores business state, job outcomes, and worker checkpoints |
| Cassandra | 1 | Serves listing and account read views |
| Kafka | 3 | Stores commands in a four-partition topic with replication factor 3 |

The topic has `min.insync.replicas=2` and seven-day retention. The setup script
creates one `consumer_offsets` row per partition in Postgres. Running setup
again preserves existing database data and checkpoints.

The baseline creates unique seller and buyer accounts, grants buyer credit,
lists an item, orders it, checks the account and listing views, and confirms
that a repeated order is rejected. It saves responses under ignored `out/`.
Each run uses new account names; it does not reset the databases.

## Individual Operations

The host scripts use ports 8080 and 8081, as in Project 5. Listing and order
scripts wait for the worker's result before printing it.

- `./scripts/create-account.sh Alice` creates an account with zero credits.
  It prompts for a password or reads one from stdin.
- `./scripts/login.sh Alice` prints a login response containing a JWT after
  reading Alice's password.
- `./scripts/admin-login.sh` logs in with the generated admin password.
- `./scripts/grant-credits.sh Bob 100` grants Bob 100 credits.
- `./scripts/list.sh Alice "Used textbook" 25` submits a listing and prints the
  completed listing or an error.
- `./scripts/browse.sh` returns available listings. An optional seller ID
  filters the result.
- `./scripts/order.sh listing-1 Bob` submits an order and prints the completed
  order or an error. Use the listing ID returned by `list.sh`.
- `./scripts/account.sh Bob 2000-01-01 2000-01-02` reads Bob's balance and
  activity, optionally within a date range.
- `./scripts/wait-job.sh Alice <job_id>` waits for a particular job result.
- `./deploy_apps.sh` rebuilds and restarts the application Pods after a code
  change while preserving database data.
- `./destroy_cluster.sh` deletes the Project 6 cluster and its data.

When `AUTH_ENABLED=true`, set `TOKEN` to the appropriate Bearer JWT for the
marketplace scripts. Browsing remains public. The cluster setup generates
signing keys and an admin password under ignored `secrets/`.

## Source Structure

```text
kind-cluster.yaml                  one control-plane node, five workers, host ports
k8s/databases.yaml                Postgres and Cassandra Services and StatefulSets
k8s/kafka.yaml                    three Kafka broker/controller Pods
k8s/apps.yaml                     login, marketplace API, and worker Deployments
database/schema.sql               business, job, and consumer checkpoint tables
create_cluster.sh                 create cluster, databases, and Kafka topic
deploy_apps.sh                    build images and deploy applications
run_baseline.sh                   end-to-end marketplace check
login-service/                    account registration and login
marketplace-service/              HTTP routes and Kafka producer
marketplace-worker/               Kafka consumer and business processing
shared/model/                     request, command, job, and result types
shared/queue/                     Kafka producer and consumer configuration
shared/marketplace/               Postgres business and job operations
shared/history/                   Cassandra read views
shared/bootstrap/                 common dependency setup
scripts/                          host-side request helpers
```

## REST API and Jobs

Project 6 keeps the Project 5 request bodies for `POST /listings` and
`POST /orders`. A successful submission returns HTTP 202 with a new `job_id`,
`status: queued`, and a `status_url`. This confirms Kafka accepted the command;
it does not confirm that a listing or order was committed. The worker may later
complete or reject the job. Each submission receives a new job ID, so a
repeated order after the listing has sold becomes a separate rejected job.

`GET /accounts/{account_id}/jobs/{job_id}` returns a committed job result.
Before the worker commits it, the endpoint may return HTTP 404. The host
`list.sh` and `order.sh` scripts use `wait-job.sh` to retry the status request
and print the eventual result. When authentication is enabled, the token
subject must match the account in the status URL.

`GET /listings` reads Cassandra. `GET /accounts/{account_id}` combines the
Postgres credit balance with Cassandra listing, order, and sales views.
`POST /accounts/{account_id}/credits` still writes directly to Postgres.
The marketplace services and worker both connect to Postgres, Cassandra,
and Kafka at startup.

## Worker Recovery

All workers join one Kafka consumer group. Kafka assigns each of the four
partitions to one worker at a time. On assignment, a worker reads the
partition's next offset from Postgres. For each command it commits the business
result, terminal job outcome, and next offset in one Postgres transaction.
Kafka consumer auto-commit is disabled. A worker that stops before the
transaction commits can replay the command; one that stops afterward resumes
from the saved checkpoint.

After the Postgres commit, the worker attempts the Cassandra read-view update
once. A crash or Cassandra failure at this point can leave the read view stale
even when the job is completed.

## Useful Inspection and Troubleshooting Commands

```bash
kind get nodes --name ece573-prj06
kubectl get services,statefulsets,pods
kubectl exec kafka-0 -- /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --describe --topic marketplace.commands
kubectl exec kafka-0 -- /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic marketplace.commands --from-beginning --timeout-ms 5000 \
  --property print.partition=true --property print.offset=true
kubectl logs deployment/marketplace-service --all-pods=true --prefix=true
kubectl logs deployment/marketplace-worker --all-pods=true --prefix=true
```

