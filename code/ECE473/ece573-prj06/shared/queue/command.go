package queue

import (
	"encoding/json"
	"fmt"

	"ece573-prj06/shared/model"

	"github.com/IBM/sarama"
)

// Publish sends an encoded command to the marketplace topic using the caller's
// partition key and returns its Kafka position for tracing.
func Publish(producer sarama.SyncProducer, key string, data []byte) (int32, int64, error) {
	return producer.SendMessage(&sarama.ProducerMessage{
		Topic: CommandsTopic,
		Key:   sarama.StringEncoder(key),
		Value: sarama.ByteEncoder(data),
	})
}

// DecodeCommand checks a Kafka record and restores the submission time for
// commands published before that field was added.
func DecodeCommand(message *sarama.ConsumerMessage) (model.Command, error) {
	var command model.Command
	if err := json.Unmarshal(message.Value, &command); err != nil {
		return model.Command{}, fmt.Errorf("invalid Kafka message at %s[%d] offset %d: %w",
			message.Topic, message.Partition, message.Offset, err)
	}
	if command.SubmittedAt.IsZero() {
		command.SubmittedAt = message.Timestamp.UTC()
	}
	if message.Topic != CommandsTopic {
		return model.Command{}, fmt.Errorf("unexpected Kafka topic %s", message.Topic)
	}
	if err := command.Validate(); err != nil {
		return model.Command{}, fmt.Errorf("invalid Kafka command at %s[%d] offset %d: %w",
			message.Topic, message.Partition, message.Offset, err)
	}
	return command, nil
}
