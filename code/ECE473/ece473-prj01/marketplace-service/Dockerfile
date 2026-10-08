FROM golang:1.26-alpine AS build

WORKDIR /src
COPY go.mod ./
COPY main.go ./
COPY marketplace ./marketplace
RUN CGO_ENABLED=0 go build -o marketplace-service .

FROM alpine:3.21

WORKDIR /app
COPY --from=build /src/marketplace-service ./marketplace-service
EXPOSE 8080
CMD ["./marketplace-service"]
