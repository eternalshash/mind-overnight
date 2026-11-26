package main

import (
	"errors"
	"fmt"
	"log"
	"time"

	"ece573-prj06/shared/history"
	"ece573-prj06/shared/marketplace"
	"ece573-prj06/shared/model"
	"ece573-prj06/shared/queue"

	"github.com/IBM/sarama"
)

// consumerHandler implements sarama.ConsumerGroupHandler. Sarama can call
// ConsumeClaim concurrently for different assigned partitions, so the handler
// shares only the store and history clients across claims.
type consumerHandler struct {
	store   *marketplace.Store
	history *history.History
}

// Setup runs at the start of each group assignment. Postgres, rather than
// Kafka's committed group offset, determines where each claim resumes.
func (h *consumerHandler) Setup(session sarama.ConsumerGroupSession) error {
	for topic, partitions := range session.Claims() {
		for _, partition := range partitions {
			next, err := h.store.NextOffset(session.Context(), topic, partition)
			if err != nil {
				return fmt.Errorf("read %s[%d] checkpoint: %w", topic, partition, err)
			}
			// Sarama's ResetOffset only moves backward. Mark then Reset forces
			// the initial claim position to the Postgres checkpoint in either
			// direction; Postgres remains the authoritative recovery position.
			session.MarkOffset(topic, partition, next, "")
			session.ResetOffset(topic, partition, next, "")
			log.Printf("INFO event=partition_assigned topic=%s partition=%d next_offset=%d", topic, partition, next)
		}
	}
	return nil
}

// Cleanup runs after the claim loops stop and records which partitions leave
// this worker. Their durable progress is already in Postgres.
func (h *consumerHandler) Cleanup(session sarama.ConsumerGroupSession) error {
	for topic, partitions := range session.Claims() {
		for _, partition := range partitions {
			log.Printf("INFO event=partition_revoked topic=%s partition=%d", topic, partition)
		}
	}
	return nil
}

// ConsumeClaim processes one assigned partition in offset order until Sarama
// closes the claim or cancels the group session.
func (h *consumerHandler) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	log.Printf("INFO event=claim_started topic=%s partition=%d initial_offset=%d",
		claim.Topic(), claim.Partition(), claim.InitialOffset())
	for {
		select {
		case <-session.Context().Done():
			return nil
		case message, ok := <-claim.Messages():
			if !ok {
				return nil
			}
			command, err := queue.DecodeCommand(message)
			if err != nil {
				return err
			}
			log.Printf("INFO event=command_processing topic=%s partition=%d offset=%d job_id=%s kind=%s",
				message.Topic, message.Partition, message.Offset, command.JobID, command.Kind)
			for session.Context().Err() == nil {
				result, err := h.store.Process(session.Context(), command, message.Topic, message.Partition, message.Offset)
				if err != nil {
					if session.Context().Err() != nil {
						return nil
					}
					if errors.Is(err, marketplace.ErrOffsetGap) {
						return err
					}
					log.Printf("ERROR event=business_retry topic=%s partition=%d offset=%d error=%v",
						message.Topic, message.Partition, message.Offset, err)
					time.Sleep(2 * time.Second)
					continue
				}
				log.Printf("INFO event=checkpoint_committed topic=%s partition=%d next_offset=%d job_id=%s kind=%s skipped=%t rejected=%t conflict=%t",
					message.Topic, message.Partition, message.Offset+1, command.JobID, command.Kind,
					result.Skipped, result.Rejected, result.Conflict)
				if !result.Skipped && !result.Rejected {
					h.project(command.JobID, result)
				}
				break
			}
		}
	}
}

// project attempts the Cassandra read-view update once after the Postgres
// business result and next offset have committed.
func (h *consumerHandler) project(jobID string, result model.CommandResult) {
	var err error
	switch {
	case result.Listing != nil:
		err = h.history.WriteListing(*result.Listing)
	case result.Order != nil:
		err = h.history.WriteOrder(*result.Order)
	default:
		return
	}
	if err != nil {
		log.Printf("ERROR event=projection_failed job_id=%s error=%v", jobID, err)
	} else {
		log.Printf("INFO event=projection_succeeded job_id=%s", jobID)
	}
}
