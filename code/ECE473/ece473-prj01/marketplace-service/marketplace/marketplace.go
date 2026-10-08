// Package marketplace contains the small in-memory marketplace used in Project 1.
package marketplace

import (
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"
)

var (
	ErrInvalidListing     = errors.New("seller_id, title, and positive credit_cost are required")
	ErrInvalidOrder       = errors.New("listing_id and buyer_id are required")
	ErrListingNotFound    = errors.New("listing not found")
	ErrListingUnavailable = errors.New("listing is no longer available")
)

// Listing is one item offered by a seller. Project 1 deliberately has no quantity:
// one successful order changes its status from available to sold.
type Listing struct {
	ListingID  string `json:"listing_id"`
	SellerID   string `json:"seller_id"`
	Title      string `json:"title"`
	CreditCost int    `json:"credit_cost"`
	Status     string `json:"status"`
	ListedAt   string `json:"listed_at"`
}

// Order records the completed synchronous checkout of one listing.
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

// Store holds Project 1 state in memory. It is safe for concurrent HTTP requests.
type Store struct {
	mu            sync.Mutex
	listings      map[string]Listing
	orders        map[string]Order
	nextListingID int
	nextOrderID   int
}

// NewStore creates an empty marketplace.
func NewStore() *Store {
	return &Store{
		listings: make(map[string]Listing),
		orders:   make(map[string]Order),
	}
}

// CreateListing makes one available item visible to shoppers.
func (s *Store) CreateListing(sellerID, title string, creditCost int) (Listing, error) {
	sellerID = strings.TrimSpace(sellerID)
	title = strings.TrimSpace(title)
	if sellerID == "" || title == "" || creditCost <= 0 {
		return Listing{}, ErrInvalidListing
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	s.nextListingID++
	listing := Listing{
		ListingID:  fmt.Sprintf("listing-%d", s.nextListingID),
		SellerID:   sellerID,
		Title:      title,
		CreditCost: creditCost,
		Status:     "available",
		ListedAt:   time.Now().UTC().Format(time.RFC3339),
	}
	s.listings[listing.ListingID] = listing
	return listing, nil
}

// AvailableListings returns available items.
func (s *Store) AvailableListings() []Listing {
	s.mu.Lock()
	defer s.mu.Unlock()

	listings := make([]Listing, 0, len(s.listings))
	for _, listing := range s.listings {
		if listing.Status == "available" {
			listings = append(listings, listing)
		}
	}
	return listings
}

// CreateOrder records an order and makes its listing unavailable atomically.
func (s *Store) CreateOrder(listingID, buyerID string) (Order, error) {
	listingID = strings.TrimSpace(listingID)
	buyerID = strings.TrimSpace(buyerID)
	if listingID == "" || buyerID == "" {
		return Order{}, ErrInvalidOrder
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	listing, ok := s.listings[listingID]
	if !ok {
		return Order{}, ErrListingNotFound
	}
	if listing.Status != "available" {
		return Order{}, ErrListingUnavailable
	}

	s.nextOrderID++
	order := Order{
		OrderID:     fmt.Sprintf("order-%d", s.nextOrderID),
		ListingID:   listing.ListingID,
		BuyerID:     buyerID,
		SellerID:    listing.SellerID,
		Title:       listing.Title,
		CreditCost:  listing.CreditCost,
		Status:      "processed",
		ListedAt:    listing.ListedAt,
		OrderedAt:   time.Now().UTC().Format(time.RFC3339),
		ProcessedAt: time.Now().UTC().Format(time.RFC3339),
	}
	listing.Status = "sold"
	s.listings[listing.ListingID] = listing
	s.orders[order.OrderID] = order
	return order, nil
}
