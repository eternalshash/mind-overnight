package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"

	"marketplace-service/marketplace"
)

type createListingRequest struct {
	SellerID   string `json:"seller_id"`
	Title      string `json:"title"`
	CreditCost int    `json:"credit_cost"`
}

type createOrderRequest struct {
	ListingID string `json:"listing_id"`
	BuyerID   string `json:"buyer_id"`
}

func main() {
	store := marketplace.NewStore()
	http.HandleFunc("/listings", listingsHandler(store))
	http.HandleFunc("/orders", ordersHandler(store))

	log.Println("marketplace service listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func listingsHandler(store *marketplace.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodPost:
			var request createListingRequest
			if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
				writeError(w, http.StatusBadRequest, "invalid JSON request")
				return
			}

			listing, err := store.CreateListing(request.SellerID, request.Title, request.CreditCost)
			if err != nil {
				writeError(w, http.StatusBadRequest, err.Error())
				return
			}
			log.Printf("created %s for seller %s", listing.ListingID, listing.SellerID)
			writeJSON(w, http.StatusCreated, listing)

		case http.MethodGet:
			writeJSON(w, http.StatusOK, map[string]any{"listings": store.AvailableListings()})

		default:
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		}
	}
}

func ordersHandler(store *marketplace.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}

		var request createOrderRequest
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON request")
			return
		}

		order, err := store.CreateOrder(request.ListingID, request.BuyerID)
		if err != nil {
			switch {
			case errors.Is(err, marketplace.ErrInvalidOrder):
				writeError(w, http.StatusBadRequest, err.Error())
			case errors.Is(err, marketplace.ErrListingNotFound):
				writeError(w, http.StatusNotFound, err.Error())
			case errors.Is(err, marketplace.ErrListingUnavailable):
				writeError(w, http.StatusConflict, err.Error())
			default:
				writeError(w, http.StatusInternalServerError, "cannot create order")
			}
			return
		}

		log.Printf("processed %s for listing %s", order.OrderID, order.ListingID)
		writeJSON(w, http.StatusCreated, order)
	}
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
