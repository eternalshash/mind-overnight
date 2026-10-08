package main

import (
	"crypto/ed25519"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"

	"ece573-prj03/auth"
	"ece573-prj03/marketplace-service/marketplace"
)

func main() {
	store, err := openStore()
	if err != nil {
		log.Fatal(err)
	}
	defer store.Close()

	enabled := strings.ToLower(os.Getenv("AUTH_ENABLED"))
	if enabled == "" {
		enabled = "false"
	}
	if enabled != "true" && enabled != "false" {
		log.Fatal("AUTH_ENABLED must be true or false")
	}
	var public ed25519.PublicKey
	if enabled == "true" {
		public, err = auth.LoadPublicKey(requiredEnvironment("JWT_PUBLIC_KEY_FILE"))
		if err != nil {
			log.Fatal(err)
		}
	} else {
		log.Println("WARNING: authentication disabled; use only for course development")
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(http.StatusNoContent) })
	if enabled == "false" {
		mux.HandleFunc("POST /listings", createListingHandler(store))
		mux.HandleFunc("POST /orders", createOrderHandler(store))
		mux.HandleFunc("GET /accounts/{account_id}", accountHandler(store))
		mux.HandleFunc("POST /accounts/{account_id}/credits", grantCreditsHandler(store))
	} else {
		mux.HandleFunc("POST /listings", requireAuthorization(
			public, matchBody("seller_id"), allowRole("user"), createListingHandler(store),
		))
		// TODO Project 3: use the listings route above as an example and add
		// requireAuthorization-wrapped registrations for these three routes:
		// 1. POST /orders: matchBody("buyer_id"), allowRole("user").
		// 2. GET /accounts/{account_id}: matchPath("account_id"), allowAny().
		// 3. POST /accounts/{account_id}/credits: matchAny(), allowRole("admin").
		mux.HandleFunc("POST /orders", requireAuthorization(
			public, matchBody("buyer_id"), allowRole("user"), createOrderHandler(store),
		))
		mux.HandleFunc("GET /accounts/{account_id}", requireAuthorization(
			public, matchPath("account_id"), allowAny(), accountHandler(store),
		))
		mux.HandleFunc("POST /accounts/{account_id}/credits", requireAuthorization(
			public, matchAny(), allowRole("admin"), grantCreditsHandler(store),
		))
	}
	mux.HandleFunc("GET /listings", browseListingsHandler(store))

	log.Println("marketplace service listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", mux))
}

func openStore() (*marketplace.Store, error) {
	config := marketplace.DatabaseConfig{
		Host:     requiredEnvironment("POSTGRES_HOST"),
		Port:     requiredEnvironment("POSTGRES_PORT"),
		Database: requiredEnvironment("POSTGRES_DB"),
		User:     requiredEnvironment("POSTGRES_USER"),
		Password: requiredEnvironment("POSTGRES_PASSWORD"),
	}
	return marketplace.OpenStore(config)
}

func requiredEnvironment(name string) string {
	value := os.Getenv(name)
	if value == "" {
		panic(fmt.Sprintf("required environment variable %s is not set", name))
	}
	return value
}
