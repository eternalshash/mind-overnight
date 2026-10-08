package marketplace

import (
	"fmt"
	"strings"
	"time"
)

// CreateListing stores one available item.
func (s *Store) CreateListing(sellerID, title string, creditCost int) (Listing, error) {
	sellerID = strings.TrimSpace(sellerID)
	title = strings.TrimSpace(title)
	if sellerID == "" || title == "" || creditCost <= 0 {
		return Listing{}, ErrInvalidListing
	}

	var accountExists bool
	err := s.db.QueryRow(
		"SELECT EXISTS (SELECT 1 FROM accounts WHERE account_id = $1)",
		sellerID,
	).Scan(&accountExists)
	if err != nil {
		return Listing{}, fmt.Errorf("check seller account: %w", err)
	}
	if !accountExists {
		return Listing{}, ErrAccountNotFound
	}

	var listing Listing
	var listedAt time.Time
	err = s.db.QueryRow(`
		INSERT INTO listings (seller_id, title, credit_cost)
		VALUES ($1, $2, $3)
		RETURNING listing_id, seller_id, title, credit_cost, status, listed_at`,
		sellerID, title, creditCost,
	).Scan(
		&listing.ListingID,
		&listing.SellerID,
		&listing.Title,
		&listing.CreditCost,
		&listing.Status,
		&listedAt,
	)
	if err != nil {
		return Listing{}, fmt.Errorf("create listing: %w", err)
	}
	listing.ListedAt = formatTime(listedAt)
	return listing, nil
}

// AvailableListings returns available items, optionally restricted to one seller.
func (s *Store) AvailableListings(sellerID string) ([]Listing, error) {
	sellerID = strings.TrimSpace(sellerID)
	query := `
		SELECT listing_id, seller_id, title, credit_cost, status, listed_at
		FROM listings
		WHERE status = 'available'
		ORDER BY listed_at, listing_id`
	args := []any{}
	if sellerID != "" {
		query = `
			SELECT listing_id, seller_id, title, credit_cost, status, listed_at
			FROM listings
			WHERE status = 'available' AND seller_id = $1
			ORDER BY listed_at, listing_id`
		args = append(args, sellerID)
	}

	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("query available listings: %w", err)
	}
	defer rows.Close()

	return scanListings(rows)
}
