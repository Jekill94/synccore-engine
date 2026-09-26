# ❌ Prima
# FROM golang:1.21-alpine AS builder

FROM golang:alpine AS builder
WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go build -o ingester main.go

FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/ingester .
EXPOSE 8080
CMD ["./ingester"]