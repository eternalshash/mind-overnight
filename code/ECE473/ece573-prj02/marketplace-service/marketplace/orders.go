package marketplace

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"
)

// CreateOrder sells one listing and records the completed order in a database
// transaction. Students complete the insufficient-credit check of this transaction.
func (s *Store) CreateOrder(listingID, buyerID string) (Order, error) {
	listingID = strings.TrimSpace(listingID)
	buyerID = strings.TrimSpace(buyerID)
	if listingID == "" || buyerID == "" {
		return Order{}, ErrInvalidOrder
	}

	tx, err := s.db.BeginTx(context.Background(), &sql.TxOptions{Isolation: sql.LevelSerializable})
	if err != nil {
		return Order{}, fmt.Errorf("begin checkout: %w", err)
	}
	defer tx.Rollback()

	var listing Listing
	var listedAt time.Time
	err = tx.QueryRow(`
		SELECT listing_id, seller_id, title, credit_cost, status, listed_at
		FROM listings
		WHERE listing_id = $1
		FOR UPDATE`,
		listingID,
	).Scan(
		&listing.ListingID,
		&listing.SellerID,
		&listing.Title,
		&listing.CreditCost,
		&listing.Status,
		&listedAt,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return Order{}, ErrListingNotFound
	}
	if err != nil {
		return Order{}, fmt.Errorf("read listing for checkout: %w", err)
	}
	if listing.Status != "available" {
		return Order{}, ErrListingUnavailable
	}

	if listing.SellerID == buyerID {
		return Order{}, ErrSelfPurchase
	}

	accountIDs := []string{buyerID, listing.SellerID}
	if accountIDs[0] > accountIDs[1] {
		accountIDs[0], accountIDs[1] = accountIDs[1], accountIDs[0]
	}

	var buyerBalance int
	// Lock both accounts in a consistent order to avoid buyer/seller deadlocks.
	for _, accountID := range accountIDs {
		var balance int
		err = tx.QueryRow(`
			SELECT balance
			FROM accounts
			WHERE account_id = $1
			FOR UPDATE`,
			accountID,
		).Scan(&balance)
		if errors.Is(err, sql.ErrNoRows) {
			return Order{}, ErrAccountNotFound
		}
		if err != nil {
			return Order{}, fmt.Errorf("lock checkout account: %w", err)
		}
		if accountID == buyerID {
			buyerBalance = balance
		}
	}

	// Return ErrInsufficientCredit when buyer has less credit than the listing cost.
	if buyerBalance < listing.CreditCost {
		return Order{}, ErrInsufficientCredit
	}

	_, err = tx.Exec(`
		UPDATE accounts
		SET balance = balance - $1
		WHERE account_id = $2`,
		listing.CreditCost,
		buyerID,
	)
	if err != nil {
		return Order{}, fmt.Errorf("debit buyer account: %w", err)
	}

	_, err = tx.Exec(`
		UPDATE accounts
		SET balance = balance + $1
		WHERE account_id = $2`,
		listing.CreditCost,
		listing.SellerID,
	)
	if err != nil {
		return Order{}, fmt.Errorf("credit seller account: %w", err)
	}

	_, err = tx.Exec(
		"UPDATE listings SET status = 'sold' WHERE listing_id = $1",
		listing.ListingID,
	)
	if err != nil {
		return Order{}, fmt.Errorf("sell listing: %w", err)
	}

	var order Order
	var orderListedAt, orderedAt, processedAt time.Time
	err = tx.QueryRow(`
		INSERT INTO orders (
			listing_id, buyer_id, seller_id, title, credit_cost, status, listed_at,
			processed_at
		)
		VALUES ($1, $2, $3, $4, $5, 'completed', $6, statement_timestamp())
		RETURNING order_id, listing_id, buyer_id, seller_id, title, credit_cost,
			status, listed_at, ordered_at, processed_at`,
		listing.ListingID,
		buyerID,
		listing.SellerID,
		listing.Title,
		listing.CreditCost,
		listedAt,
	).Scan(
		&order.OrderID,
		&order.ListingID,
		&order.BuyerID,
		&order.SellerID,
		&order.Title,
		&order.CreditCost,
		&order.Status,
		&orderListedAt,
		&orderedAt,
		&processedAt,
	)
	if err != nil {
		return Order{}, fmt.Errorf("record order: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return Order{}, fmt.Errorf("commit checkout: %w", err)
	}

	order.ListedAt = formatTime(orderListedAt)
	order.OrderedAt = formatTime(orderedAt)
	order.ProcessedAt = formatTime(processedAt)
	return order, nil
}
