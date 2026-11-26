package main

import (
	"context"
	"log"
	"os/signal"
	"syscall"
	"time"

	"ece573-prj06/shared/bootstrap"
	"ece573-prj06/shared/queue"
)

func main() {
	store, h, q, err := bootstrap.Open()
	if err != nil {
		log.Fatal("FATAL initialize dependencies: ", err)
	}
	defer store.Close()
	defer h.Close()
	defer q.Close()

	group, err := q.NewConsumerGroup("marketplace-workers")
	if err != nil {
		log.Fatal(err)
	}
	defer group.Close()

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	handler := &consumerHandler{store: store, history: h}
	for ctx.Err() == nil {
		if err := group.Consume(ctx, []string{queue.CommandsTopic}, handler); err != nil && ctx.Err() == nil {
			log.Printf("ERROR Kafka consumer group: %v", err)
			time.Sleep(2 * time.Second)
		}
	}
}
