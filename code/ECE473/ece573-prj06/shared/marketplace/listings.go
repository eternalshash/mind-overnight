package marketplace

import (
	"database/sql"
	"fmt"
	"strings"
	"time"

	"ece573-prj06/shared/model"
)

// createListingTx stores one available item inside the worker's offset transaction.
func createListingTx(tx *sql.Tx, sellerID, title string, creditCost int, submittedAt time.Time) (model.Listing, error) {
	sellerID = strings.TrimSpace(sellerID)
	title = strings.TrimSpace(title)
	if sellerID == "" || title == "" || creditCost <= 0 {
		return model.Listing{}, ErrInvalidListing
	}

	var accountExists bool
	err := tx.QueryRow(
		"SELECT EXISTS (SELECT 1 FROM accounts WHERE account_id = $1)",
		sellerID,
	).Scan(&accountExists)
	if err != nil {
		return model.Listing{}, fmt.Errorf("check seller account: %w", err)
	}
	if !accountExists {
		return model.Listing{}, ErrAccountNotFound
	}

	var listing model.Listing
	var listedAt time.Time
	err = tx.QueryRow(`
		INSERT INTO listings (seller_id, title, credit_cost, listed_at)
		VALUES ($1, $2, $3, $4)
		RETURNING listing_id, seller_id, title, credit_cost, status, listed_at`,
		sellerID, title, creditCost, submittedAt,
	).Scan(
		&listing.ListingID,
		&listing.SellerID,
		&listing.Title,
		&listing.CreditCost,
		&listing.Status,
		&listedAt,
	)
	if err != nil {
		return model.Listing{}, fmt.Errorf("create listing: %w", err)
	}
	listing.ListedAt = formatTime(listedAt)
	return listing, nil
}
