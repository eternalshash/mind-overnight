package main

import (
	"fmt"
	"log"
	"net/http"
	"os"

	"marketplace-service/marketplace"
)

func main() {
	store, err := openStore()
	if err != nil {
		log.Fatal(err)
	}
	defer store.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("POST /accounts", createAccountHandler(store))
	mux.HandleFunc("POST /listings", createListingHandler(store))
	mux.HandleFunc("GET /listings", browseListingsHandler(store))
	mux.HandleFunc("POST /orders", createOrderHandler(store))
	mux.HandleFunc("GET /accounts/{account_id}", accountHandler(store))

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
