// Package model contains marketplace requests and results shared by the API, worker, and stores.
package model

import (
	"encoding/json"
	"time"
)

// ListingRequest is the data submitted to create a listing.
type ListingRequest struct {
	SellerID   string `json:"seller_id"`
	Title      string `json:"title"`
	CreditCost int    `json:"credit_cost"`
}

// OrderRequest is the data submitted to buy a listing.
type OrderRequest struct {
	ListingID string `json:"listing_id"`
	BuyerID   string `json:"buyer_id"`
}

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

// JobOutcome is the durable status returned for an asynchronous submission.
type JobOutcome struct {
	JobID       string          `json:"job_id"`
	Kind        string          `json:"kind"`
	ActorID     string          `json:"actor_id"`
	SubmittedAt time.Time       `json:"submitted_at"`
	Status      string          `json:"status"`
	Result      json.RawMessage `json:"result,omitempty"`
	ErrorCode   string          `json:"error_code,omitempty"`
}
