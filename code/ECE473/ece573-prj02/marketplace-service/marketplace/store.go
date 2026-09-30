// Package marketplace contains the Postgres-backed marketplace used in Project 2.
package marketplace

import (
	"database/sql"
	"errors"
	"fmt"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
)

var (
	ErrInvalidListing         = errors.New("seller_id, title, and positive credit_cost are required")
	ErrInvalidOrder           = errors.New("listing_id and buyer_id are required")
	ErrInvalidAccount         = errors.New("account_id is required")
	ErrInvalidAccountCreation = errors.New("account_id and a nonnegative starting_balance are required")
	ErrAccountNotFound        = errors.New("account not found")
	ErrAccountExists          = errors.New("account already exists")
	ErrListingNotFound        = errors.New("listing not found")
	ErrListingUnavailable     = errors.New("listing is no longer available")
	ErrInsufficientCredit     = errors.New("buyer has insufficient credit")
	ErrSelfPurchase           = errors.New("seller cannot buy their own listing")
)

// Listing is one item offered by a seller.
type Listing struct {
	ListingID  string `json:"listing_id"`
	SellerID   string `json:"seller_id"`
	Title      string `json:"title"`
	CreditCost int    `json:"credit_cost"`
	Status     string `json:"status"`
	ListedAt   string `json:"listed_at"`
}

// Order records a buyer's request and its outcome. A completed order is a
// purchase for the buyer and a sale for the seller.
type Order struct {
	OrderID     string `json:"order_id"`
	ListingID   string `json:"listing_id"`
	BuyerID     string `json:"buyer_id"`
	SellerID    string `json:"seller_id"`
	Title       string `json:"title"`
	CreditCost  int    `json:"credit_cost"`
	Status      string `json:"status"`
	ListedAt    string `json:"listed_at"`
	OrderedAt   string `json:"ordered_at"`
	ProcessedAt string `json:"processed_at"`
}

// Account is the account-oriented read view used by buyers and sellers.
type Account struct {
	AccountID string    `json:"account_id"`
	Balance   int       `json:"balance"`
	Listings  []Listing `json:"listings"`
	Orders    []Order   `json:"orders"`
	Sales     []Order   `json:"sales"`
}

// DatabaseConfig contains the Compose-provided Postgres connection settings.
type DatabaseConfig struct {
	Host     string
	Port     string
	Database string
	User     string
	Password string
}

// Store provides marketplace operations backed by Postgres.
type Store struct {
	db *sql.DB
}

// OpenStore connects to Postgres and waits briefly for it to become ready.
func OpenStore(config DatabaseConfig) (*Store, error) {
	connection := fmt.Sprintf(
		"host=%s port=%s dbname=%s user=%s password=%s sslmode=disable",
		config.Host, config.Port, config.Database, config.User, config.Password,
	)
	db, err := sql.Open("pgx", connection)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	var pingErr error
	for range 30 {
		pingErr = db.Ping()
		if pingErr == nil {
			return &Store{db: db}, nil
		}
		time.Sleep(time.Second)
	}
	db.Close()
	return nil, fmt.Errorf("connect to database: %w", pingErr)
}

// Close releases the database connection pool.
func (s *Store) Close() error {
	return s.db.Close()
}

func scanListings(rows *sql.Rows) ([]Listing, error) {
	listings := []Listing{}
	for rows.Next() {
		var listing Listing
		var listedAt time.Time
		if err := rows.Scan(
			&listing.ListingID,
			&listing.SellerID,
			&listing.Title,
			&listing.CreditCost,
			&listing.Status,
			&listedAt,
		); err != nil {
			return nil, fmt.Errorf("scan listing: %w", err)
		}
		listing.ListedAt = formatTime(listedAt)
		listings = append(listings, listing)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("read listings: %w", err)
	}
	return listings, nil
}

func scanOrders(rows *sql.Rows) ([]Order, error) {
	orders := []Order{}
	for rows.Next() {
		var order Order
		var listedAt, orderedAt, processedAt time.Time
		if err := rows.Scan(
			&order.OrderID,
			&order.ListingID,
			&order.BuyerID,
			&order.SellerID,
			&order.Title,
			&order.CreditCost,
			&order.Status,
			&listedAt,
			&orderedAt,
			&processedAt,
		); err != nil {
			return nil, fmt.Errorf("scan order: %w", err)
		}
		order.ListedAt = formatTime(listedAt)
		order.OrderedAt = formatTime(orderedAt)
		order.ProcessedAt = formatTime(processedAt)
		orders = append(orders, order)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("read orders: %w", err)
	}
	return orders, nil
}

func formatTime(value time.Time) string {
	return value.UTC().Format(time.RFC3339)
}
