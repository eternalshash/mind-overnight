// Package bootstrap opens the shared dependencies required by the marketplace API and worker.
package bootstrap

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"ece573-prj06/shared/history"
	"ece573-prj06/shared/marketplace"
	"ece573-prj06/shared/queue"
)

// Open loads the common configuration and connects to Postgres, Cassandra, then Kafka.
// The caller closes all three returned resources.
func Open() (*marketplace.Store, *history.History, *queue.Queue, error) {
	for _, name := range []string{
		"POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER",
		"POSTGRES_PASSWORD", "CASSANDRA_CONTACT_POINTS", "KAFKA_BROKERS",
	} {
		if strings.TrimSpace(os.Getenv(name)) == "" {
			return nil, nil, nil, fmt.Errorf("%s is required", name)
		}
	}

	replicas, err := strconv.Atoi(envDefault("CASSANDRA_REPLICATION_FACTOR", "1"))
	if err != nil {
		return nil, nil, nil, fmt.Errorf("CASSANDRA_REPLICATION_FACTOR: %w", err)
	}
	store, err := marketplace.OpenStore(marketplace.DatabaseConfig{
		Host: os.Getenv("POSTGRES_HOST"), Port: os.Getenv("POSTGRES_PORT"),
		Database: os.Getenv("POSTGRES_DB"), User: os.Getenv("POSTGRES_USER"),
		Password: os.Getenv("POSTGRES_PASSWORD"),
	})
	if err != nil {
		return nil, nil, nil, fmt.Errorf("Postgres: %w", err)
	}
	h, err := history.OpenHistory(history.DatabaseConfig{
		ContactPoints:     os.Getenv("CASSANDRA_CONTACT_POINTS"),
		ReplicationFactor: replicas,
		ReadConsistency:   envDefault("READ_CONSISTENCY", "QUORUM"),
		WriteConsistency:  envDefault("WRITE_CONSISTENCY", "QUORUM"),
	})
	if err != nil {
		store.Close()
		return nil, nil, nil, fmt.Errorf("Cassandra: %w", err)
	}
	q, err := queue.OpenQueue(os.Getenv("KAFKA_BROKERS"))
	if err != nil {
		h.Close()
		store.Close()
		return nil, nil, nil, fmt.Errorf("Kafka: %w", err)
	}
	return store, h, q, nil
}

func envDefault(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}
