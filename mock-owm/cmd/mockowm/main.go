package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	owminternal "github.com/MrSody71/weather-pipeline/mock-owm/internal"
)

func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rw := &responseWriter{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rw, r)
		slog.Info("request",
			"method", r.Method,
			"path", r.URL.Path,
			"status", rw.status,
			"latency", time.Since(start).String(),
		)
	})
}

type responseWriter struct {
	http.ResponseWriter
	status int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.status = code
	rw.ResponseWriter.WriteHeader(code)
}

func main() {
	addr := os.Getenv("MOCK_OWM_ADDR")
	if addr == "" {
		addr = ":8081"
	}

	seedStr := os.Getenv("MOCK_OWM_SEED")
	var seed int64
	if seedStr != "" {
		if v, err := strconv.ParseInt(seedStr, 10, 64); err == nil {
			seed = v
		}
	}
	if seed == 0 {
		seed = time.Now().UnixNano()
	}
	owminternal.Init(seed)
	slog.Info("rand seed", "seed", seed)

	mux := http.NewServeMux()
	mux.HandleFunc("/health", owminternal.HealthHandler)
	mux.HandleFunc("/data/2.5/weather", owminternal.WeatherHandler)
	mux.HandleFunc("/batch", owminternal.BatchHandler)

	srv := &http.Server{
		Addr:         addr,
		Handler:      loggingMiddleware(mux),
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  30 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	go func() {
		slog.Info("mock-owm starting", "addr", addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			slog.Error("server error", "err", err)
			os.Exit(1)
		}
	}()

	<-ctx.Done()
	slog.Info("shutting down...")

	shutCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutCtx); err != nil {
		slog.Error("shutdown error", "err", err)
	}
	slog.Info("stopped")
}
