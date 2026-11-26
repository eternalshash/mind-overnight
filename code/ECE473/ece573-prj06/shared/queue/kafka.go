// Package queue contains the Kafka transport used by the marketplace API and worker.
package queue

import (
	"fmt"
	"strings"

	"github.com/IBM/sarama"
)

const CommandsTopic = "marketplace.commands"

// Queue owns the Kafka client shared by one process's producer or consumer group.
type Queue struct {
	client sarama.Client
}

// OpenQueue connects to Kafka with the configuration shared by the API and worker.
func OpenQueue(brokerList string) (*Queue, error) {
	config, err := kafkaConfig()
	if err != nil {
		return nil, fmt.Errorf("config: %w", err)
	}
	client, err := sarama.NewClient(brokers(brokerList), config)
	if err != nil {
		return nil, err
	}
	return &Queue{client: client}, nil
}

// NewProducer creates the API's producer. Close it before closing the Queue.
func (q *Queue) NewProducer() (sarama.SyncProducer, error) {
	return sarama.NewSyncProducerFromClient(q.client)
}

// NewConsumerGroup creates a worker's consumer group. Close it before closing the Queue.
func (q *Queue) NewConsumerGroup(groupID string) (sarama.ConsumerGroup, error) {
	return sarama.NewConsumerGroupFromClient(groupID, q.client)
}

// Close releases the Kafka client.
func (q *Queue) Close() error {
	return q.client.Close()
}

func brokers(value string) []string {
	var result []string
	for _, broker := range strings.Split(value, ",") {
		if broker = strings.TrimSpace(broker); broker != "" {
			result = append(result, broker)
		}
	}
	return result
}

func kafkaConfig() (*sarama.Config, error) {
	config := sarama.NewConfig()
	version, err := sarama.ParseKafkaVersion("4.0.0")
	if err != nil {
		return nil, err
	}
	config.Version = version
	config.Producer.RequiredAcks = sarama.WaitForAll
	config.Producer.Return.Successes = true
	config.Producer.Idempotent = true
	config.Producer.Retry.Max = 5
	config.Net.MaxOpenRequests = 1
	config.Consumer.Offsets.AutoCommit.Enable = false
	config.Consumer.Offsets.Initial = sarama.OffsetOldest
	config.Consumer.Group.ResetInvalidOffsets = false
	return config, config.Validate()
}
