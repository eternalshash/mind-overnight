package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strings"

	"marketplace-service/marketplace"
)

type createListingRequest struct {
	SellerID   string `json:"seller_id"`
	Title      string `json:"title"`
	CreditCost int    `json:"credit_cost"`
}

type createAccountRequest struct {
	AccountID       string `json:"account_id"`
	StartingBalance *int   `json:"starting_balance"`
}

type createOrderRequest struct {
	ListingID string `json:"listing_id"`
	BuyerID   string `json:"buyer_id"`
}

func createAccountHandler(store *marketplace.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var request createAccountRequest
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON request")
			return
		}
		if request.StartingBalance == nil {
			writeMarketplaceError(w, marketplace.ErrInvalidAccountCreation)
			return
		}

		account, err := store.CreateAccount(request.AccountID, *request.StartingBalance)
		if err != nil {
			writeMarketplaceError(w, err)
			return
		}

		log.Printf("created account %s", account.AccountID)
		writeJSON(w, http.StatusCreated, account)
	}
}

func createListingHandler(store *marketplace.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var request createListingRequest
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON request")
			return
		}

		listing, err := store.CreateListing(request.SellerID, request.Title, request.CreditCost)
		if err != nil {
			writeMarketplaceError(w, err)
			return
		}

		log.Printf("created %s for seller %s", listing.ListingID, listing.SellerID)
		writeJSON(w, http.StatusCreated, listing)
	}
}

func browseListingsHandler(store *marketplace.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		sellerID := strings.TrimSpace(r.URL.Query().Get("seller_id"))
		listings, err := store.AvailableListings(sellerID)
		if err != nil {
			writeMarketplaceError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"listings": listings})
	}
}

func createOrderHandler(store *marketplace.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var request createOrderRequest
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON request")
			return
		}

		order, err := store.CreateOrder(request.ListingID, request.BuyerID)
		if err != nil {
			writeMarketplaceError(w, err)
			return
		}

		log.Printf("completed %s for listing %s", order.OrderID, order.ListingID)
		writeJSON(w, http.StatusCreated, order)
	}
}

func accountHandler(store *marketplace.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		accountID := strings.TrimSpace(r.PathValue("account_id"))
		account, err := store.GetAccount(accountID)
		if err != nil {
			writeMarketplaceError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, account)
	}
}

func writeMarketplaceError(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, marketplace.ErrInvalidListing),
		errors.Is(err, marketplace.ErrInvalidOrder),
		errors.Is(err, marketplace.ErrInvalidAccount),
		errors.Is(err, marketplace.ErrInvalidAccountCreation):
		writeError(w, http.StatusBadRequest, err.Error())
	case errors.Is(err, marketplace.ErrAccountNotFound),
		errors.Is(err, marketplace.ErrListingNotFound):
		writeError(w, http.StatusNotFound, err.Error())
	case errors.Is(err, marketplace.ErrListingUnavailable),
		errors.Is(err, marketplace.ErrInsufficientCredit),
		errors.Is(err, marketplace.ErrAccountExists),
		errors.Is(err, marketplace.ErrSelfPurchase):
		writeError(w, http.StatusConflict, err.Error())
	default:
		log.Printf("marketplace operation failed: %v", err)
		writeError(w, http.StatusInternalServerError, "marketplace operation failed")
	}
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(value); err != nil {
		log.Printf("cannot encode response: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
