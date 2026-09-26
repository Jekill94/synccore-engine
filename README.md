# 🚀 SyncCore Engine

> Una piattaforma microservizi B2B/SaaS progettata per l'ingestione ad alte prestazioni, la gestione e l'analisi automatizzata tramite Intelligenza Artificiale di lead ed eventi aziendali.

[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](https://www.docker.com/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?logo=go)](https://golang.org/)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python)](https://python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org/)

---

## Architettura dei Servizi

Il sistema è suddiviso in 4 servizi isolati che comunicano all'interno di una rete Docker dedicata:

*   **`synccore_frontend` (Porta 3000):** Dashboard utente sviluppata con **Next.js 16 (App Router)**, TypeScript e Tailwind CSS per il monitoraggio in tempo reale.
*   **`synccore_ingester` (Porta 8080):** Service Layer ad altissime performance scritto in **Go (Golang)** per la validazione istantanea delle API Key e il routing dei payload.
*   **`synccore_backend` (Porta 5000):** Core business logic in **Python (Flask)**. Gestisce l'hashing sicuro (`bcrypt`), la registrazione e l'interfacciamento con modelli LLM (Ollama/Llama3) per l'analisi AI.
*   **`synccore_db` (Porta 3306):** Database relazionale **MySQL 8.0**.

---

## Come Avviare il Progetto (Docker)

Assicurati di avere installato **Docker** e **Docker Compose** sulla tua macchina.

1. Clona la repository:
   ```bash
   git clone [https://github.com/Jekill94/synccore-engine.git](https://github.com/Jekill94/synccore-engine.git)
   cd synccore-engine
