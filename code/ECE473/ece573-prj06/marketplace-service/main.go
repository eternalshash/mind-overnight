package main

import (
	"crypto/ed25519"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"

	"ece573-prj06/auth"
	"ece573-prj06/shared/bootstrap"
)

func main() {
	store, history, q, err := bootstrap.Open()
	if err != nil {
		log.Fatal("FATAL initialize dependencies: ", err)
	}
	defer store.Close()
	defer history.Close()
	defer q.Close()

	producer, err := q.NewProducer()
	if err != nil {
		log.Fatal("FATAL Kafka producer: ", err)
	}
	defer producer.Close()

	enabled := strings.ToLower(os.Getenv("AUTH_ENABLED"))
	if enabled == "" {
		enabled = "false"
	}
	if enabled != "true" && enabled != "false" {
		log.Fatal("FATAL AUTH_ENABLED must be true or false")
	}
	var public ed25519.PublicKey
	if enabled == "true" {
		public, err = auth.LoadPublicKey(requiredEnvironment("JWT_PUBLIC_KEY_FILE"))
		if err != nil {
			log.Fatal("FATAL load JWT public key: ", err)
		}
	} else {
		log.Println("WARN authentication disabled; use only for course development")
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(http.StatusNoContent) })
	if enabled == "false" {
		mux.HandleFunc("POST /listings", submitListingHandler(producer))
		mux.HandleFunc("POST /orders", submitOrderHandler(producer))
		mux.HandleFunc("GET /accounts/{account_id}", accountHandler(store, history))
		mux.HandleFunc("POST /accounts/{account_id}/credits", grantCreditsHandler(store))
		mux.HandleFunc("GET /accounts/{account_id}/jobs/{job_id}", getJobHandler(store))
	} else {
		mux.HandleFunc("POST /listings", requireAuthorization(
			public, matchBody("seller_id"), allowRole("user"), submitListingHandler(producer),
		))
		mux.HandleFunc("POST /orders", requireAuthorization(
			public, matchBody("buyer_id"), allowRole("user"), submitOrderHandler(producer),
		))
		mux.HandleFunc("GET /accounts/{account_id}", requireAuthorization(
			public, matchPath("account_id"), allowAny(), accountHandler(store, history),
		))
		mux.HandleFunc("POST /accounts/{account_id}/credits", requireAuthorization(
			public, matchAny(), allowRole("admin"), grantCreditsHandler(store),
		))
		mux.HandleFunc("GET /accounts/{account_id}/jobs/{job_id}", requireAuthorization(
			public, matchPath("account_id"), allowAny(), getJobHandler(store),
		))
	}
	mux.HandleFunc("GET /listings", browseListingsHandler(history))

	log.Println("INFO marketplace service listening on :8080")
	log.Fatal("FATAL marketplace HTTP server: ", http.ListenAndServe(":8080", limitRequests(mux)))
}

func environmentDefault(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}

func requiredEnvironment(name string) string {
	value := os.Getenv(name)
	if value == "" {
		panic(fmt.Sprintf("required environment variable %s is not set", name))
	}
	return value
}
