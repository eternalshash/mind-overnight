package marketplace

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"

	"ece573-prj06/shared/model"
)

var ErrOffsetGap = errors.New("Kafka offset does not match Postgres checkpoint")

func (s *Store) GetJob(ctx context.Context, jobID string) (model.JobOutcome, error) {
	var job model.JobOutcome
	var result []byte
	var errorCode sql.NullString
	err := s.db.QueryRowContext(ctx, `
		SELECT job_id, kind, actor_id, submitted_at, status, result, error_code
		FROM job_outcomes WHERE job_id = $1`, jobID,
	).Scan(&job.JobID, &job.Kind, &job.ActorID, &job.SubmittedAt, &job.Status, &result, &errorCode)
	if err != nil {
		return model.JobOutcome{}, err
	}
	job.Result = result
	job.ErrorCode = errorCode.String
	return job, nil
}

func (s *Store) NextOffset(ctx context.Context, topic string, partition int32) (int64, error) {
	var next int64
	err := s.db.QueryRowContext(ctx, `
		SELECT next_offset FROM consumer_offsets
		WHERE topic = $1 AND partition_id = $2`, topic, partition,
	).Scan(&next)
	return next, err
}

// Process atomically commits a business result and its Kafka recovery position.
func (s *Store) Process(ctx context.Context, command model.Command, topic string, partition int32, offset int64) (model.CommandResult, error) {
	tx, err := s.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
	if err != nil {
		return model.CommandResult{}, err
	}
	defer tx.Rollback()

	var next int64
	err = tx.QueryRowContext(ctx, `
		SELECT next_offset FROM consumer_offsets
		WHERE topic = $1 AND partition_id = $2 FOR UPDATE`, topic, partition,
	).Scan(&next)
	if err != nil {
		return model.CommandResult{}, fmt.Errorf("read offset checkpoint: %w", err)
	}
	if offset < next {
		return model.CommandResult{Skipped: true}, nil
	}
	if offset > next {
		return model.CommandResult{}, fmt.Errorf("%w: %s[%d] got %d, expected %d", ErrOffsetGap, topic, partition, offset, next)
	}

	insert, err := tx.ExecContext(ctx, `
		INSERT INTO job_outcomes (job_id, kind, actor_id, submitted_at, status)
		VALUES ($1, $2, $3, $4, 'processing')
		ON CONFLICT (job_id) DO NOTHING`,
		command.JobID, command.Kind, command.ActorID, command.SubmittedAt,
	)
	if err != nil {
		return model.CommandResult{}, fmt.Errorf("claim job: %w", err)
	}
	rows, err := insert.RowsAffected()
	if err != nil {
		return model.CommandResult{}, err
	}
	result := model.CommandResult{}
	if rows == 0 {
		var kind, actor string
		err = tx.QueryRowContext(ctx, `
			SELECT kind, actor_id FROM job_outcomes WHERE job_id = $1`,
			command.JobID,
		).Scan(&kind, &actor)
		if err != nil {
			return model.CommandResult{}, err
		}
		result.Skipped = true
		result.Conflict = kind != command.Kind || actor != command.ActorID
	} else {
		var payload []byte
		var businessErr error
		switch command.Kind {
		case "listing":
			request, decodeErr := command.Listing()
			if decodeErr != nil {
				return model.CommandResult{}, fmt.Errorf("decode listing payload: %w", decodeErr)
			}
			var listing model.Listing
			listing, businessErr = createListingTx(tx, request.SellerID, request.Title, request.CreditCost, command.SubmittedAt)
			if businessErr == nil {
				result.Listing = &listing
				payload, err = json.Marshal(listing)
			}
		case "order":
			request, decodeErr := command.Order()
			if decodeErr != nil {
				return model.CommandResult{}, fmt.Errorf("decode order payload: %w", decodeErr)
			}
			var order model.Order
			order, businessErr = createOrderTx(tx, request.ListingID, request.BuyerID, command.SubmittedAt)
			if businessErr == nil {
				result.Order = &order
				payload, err = json.Marshal(order)
			}
		default:
			return model.CommandResult{}, fmt.Errorf("unknown command kind %q", command.Kind)
		}
		if err != nil {
			return model.CommandResult{}, err
		}
		if businessErr != nil {
			if !isBusinessError(businessErr) {
				return model.CommandResult{}, businessErr
			}
			result.Rejected = true
			_, err = tx.ExecContext(ctx, `
				UPDATE job_outcomes SET status = 'rejected', error_code = $2, updated_at = CURRENT_TIMESTAMP
				WHERE job_id = $1`, command.JobID, businessErr.Error())
		} else {
			_, err = tx.ExecContext(ctx, `
				UPDATE job_outcomes SET status = 'completed', result = $2, updated_at = CURRENT_TIMESTAMP
				WHERE job_id = $1`, command.JobID, payload)
		}
		if err != nil {
			return model.CommandResult{}, err
		}
	}

	_, err = tx.ExecContext(ctx, `
		UPDATE consumer_offsets SET next_offset = $3
		WHERE topic = $1 AND partition_id = $2`, topic, partition, offset+1)
	if err != nil {
		return model.CommandResult{}, fmt.Errorf("advance offset checkpoint: %w", err)
	}
	if err := tx.Commit(); err != nil {
		return model.CommandResult{}, fmt.Errorf("commit business and offset: %w", err)
	}
	return result, nil
}

func isBusinessError(err error) bool {
	for _, candidate := range []error{
		ErrInvalidListing, ErrInvalidOrder, ErrAccountNotFound, ErrListingNotFound,
		ErrListingUnavailable, ErrInsufficientCredit, ErrSelfPurchase,
	} {
		if errors.Is(err, candidate) {
			return true
		}
	}
	return false
}
