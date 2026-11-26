package main

import (
	"encoding/json"
	"log"
	"net/http"
	"net/url"
	"strings"

	"ece573-prj06/shared/model"
	"ece573-prj06/shared/queue"

	"github.com/IBM/sarama"
)

func submitListingHandler(producer sarama.SyncProducer) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var request model.ListingRequest
		if err := decodeCommand(w, r, &request); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON request")
			return
		}
		request.SellerID = strings.TrimSpace(request.SellerID)
		request.Title = strings.TrimSpace(request.Title)
		if request.SellerID == "" || request.Title == "" || request.CreditCost <= 0 {
			writeError(w, http.StatusBadRequest, "seller_id, title, and positive credit_cost are required")
			return
		}
		command, err := model.NewCommand("listing", request.SellerID, request)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "cannot encode request")
			return
		}
		submit(w, producer, command, "")
	}
}

func submitOrderHandler(producer sarama.SyncProducer) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var request model.OrderRequest
		if err := decodeCommand(w, r, &request); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON request")
			return
		}
		request.ListingID = strings.TrimSpace(request.ListingID)
		request.BuyerID = strings.TrimSpace(request.BuyerID)
		if request.ListingID == "" || request.BuyerID == "" {
			writeError(w, http.StatusBadRequest, "listing_id and buyer_id are required")
			return
		}
		command, err := model.NewCommand("order", request.BuyerID, request)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "cannot encode request")
			return
		}
		submit(w, producer, command, request.ListingID)
	}
}

func decodeCommand(w http.ResponseWriter, r *http.Request, target any) error {
	r.Body = http.MaxBytesReader(w, r.Body, 64<<10)
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	return decoder.Decode(target)
}

func submit(w http.ResponseWriter, producer sarama.SyncProducer,
	command model.Command, key string) {
	var err error
	command.JobID, err = model.NewJobID()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "cannot create job ID")
		return
	}
	if key == "" {
		key = command.JobID
	}
	data, err := json.Marshal(command)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "cannot encode request")
		return
	}
	partition, offset, err := queue.Publish(producer, key, data)
	if err != nil {
		log.Printf("ERROR event=queue_publish_failed topic=%s job_id=%s kind=%s error=%v", queue.CommandsTopic, command.JobID, command.Kind, err)
		writeError(w, http.StatusServiceUnavailable, "queue unavailable")
		return
	}
	log.Printf("INFO event=queue_published topic=%s partition=%d offset=%d job_id=%s kind=%s",
		queue.CommandsTopic, partition, offset, command.JobID, command.Kind)
	writeJSON(w, http.StatusAccepted, map[string]any{
		"job_id": command.JobID, "status": "queued",
		"submitted_at": command.SubmittedAt,
		"status_url":   "/accounts/" + url.PathEscape(command.ActorID) + "/jobs/" + command.JobID,
	})
}
