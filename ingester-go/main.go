package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"

	_ "github.com/go-sql-driver/mysql"
)

var db *sql.DB

type Payload struct {
	Name    string `json:"name"`
	Email   string `json:"email"`
	Message string `json:"message"`
}

func enableCORS(w http.ResponseWriter) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type, X-API-Key, X-Employee-ID, X-Domain")
}

func isValidApiKey(apiKey string) bool {
	if db == nil {
		return true // Fallback se il DB non è connesso direttamente all'ingester
	}
	var exists bool
	query := "SELECT EXISTS(SELECT 1 FROM users WHERE api_key = ?)"
	err := db.QueryRow(query, apiKey).Scan(&exists)
	if err != nil {
		return false
	}
	return exists
}

func ingestHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)

	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusOK)
		return
	}

	if r.Method != http.MethodPost {
		http.Error(w, "Metodo non consentito", http.StatusMethodNotAllowed)
		return
	}

	apiKey := r.Header.Get("X-API-Key")
	if apiKey != "" && !isValidApiKey(apiKey) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(map[string]string{
			"error": "API Key non valida o non registrata",
		})
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Errore nella lettura del payload", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	var data Payload
	if err := json.Unmarshal(body, &data); err != nil {
		http.Error(w, "JSON non valido", http.StatusBadRequest)
		return
	}

	// Recupera l'URL del backend Python dalle variabili d'ambiente Docker
	backendURL := os.Getenv("BACKEND_URL")
	if backendURL == "" {
		backendURL = "http://backend:5000/process"
	}

	req, err := http.NewRequest("POST", backendURL, bytes.NewBuffer(body))
	if err != nil {
		http.Error(w, "Errore interno durante la creazione della richiesta", http.StatusInternalServerError)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	if apiKey != "" {
		req.Header.Set("X-API-Key", apiKey)
	}
	if empID := r.Header.Get("X-Employee-ID"); empID != "" {
		req.Header.Set("X-Employee-ID", empID)
	}
	if domain := r.Header.Get("X-Domain"); domain != "" {
		req.Header.Set("X-Domain", domain)
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, "Errore comunicazione con il motore AI Backend: "+err.Error(), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	w.Write(respBody)
}

func main() {
	var err error
	dbHost := os.Getenv("DB_HOST")
	if dbHost == "" {
		dbHost = "db"
	}

	dsn := fmt.Sprintf("root:root@tcp(%s:3306)/synccore_db", dbHost)
	db, err = sql.Open("mysql", dsn)
	if err != nil {
		log.Printf("[Go Ingester Warning] Impossibile connettersi al DB direttamente: %v", err)
	} else {
		defer db.Close()
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	http.HandleFunc("/ingest", ingestHandler)
	log.Printf("[Go Ingester] Server attivo su 0.0.0.0:%s con validazione API Key dinamica...", port)
	log.Fatal(http.ListenAndServe("0.0.0.0:"+port, nil))
}