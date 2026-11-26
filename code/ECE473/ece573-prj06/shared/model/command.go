package model

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"
)

// Command is the immutable request sent to a Kafka partition.
type Command struct {
	JobID       string          `json:"job_id"`
	Kind        string          `json:"kind"`
	ActorID     string          `json:"actor_id"`
	SubmittedAt time.Time       `json:"submitted_at"`
	Payload     json.RawMessage `json:"payload"`
}

// CommandResult carries a committed business result from the store to the worker.
type CommandResult struct {
	Listing  *Listing
	Order    *Order
	Skipped  bool
	Conflict bool
	Rejected bool
}

func NewCommand(kind, actor string, payload any) (Command, error) {
	data, err := json.Marshal(payload)
	if err != nil {
		return Command{}, err
	}
	return Command{Kind: kind, ActorID: actor, SubmittedAt: time.Now().UTC().Truncate(time.Microsecond), Payload: data}, nil
}

func (c Command) Listing() (ListingRequest, error) {
	var payload ListingRequest
	err := json.Unmarshal(c.Payload, &payload)
	return payload, err
}

func (c Command) Order() (OrderRequest, error) {
	var payload OrderRequest
	err := json.Unmarshal(c.Payload, &payload)
	return payload, err
}

func (c Command) Validate() error {
	if c.JobID == "" || c.ActorID == "" || c.SubmittedAt.IsZero() || len(c.Payload) == 0 {
		return fmt.Errorf("missing command metadata or payload")
	}
	switch c.Kind {
	case "listing":
		payload, err := c.Listing()
		if err != nil || payload.SellerID != c.ActorID {
			return fmt.Errorf("invalid listing payload or actor")
		}
	case "order":
		payload, err := c.Order()
		if err != nil || payload.BuyerID != c.ActorID {
			return fmt.Errorf("invalid order payload or actor")
		}
	default:
		return fmt.Errorf("unknown command kind %q", c.Kind)
	}
	return nil
}

// NewJobID assigns a distinct ID to each accepted submission.
func NewJobID() (string, error) {
	var id [16]byte
	if _, err := rand.Read(id[:]); err != nil {
		return "", err
	}
	return hex.EncodeToString(id[:]), nil
}
