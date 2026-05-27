#!/usr/bin/env bash
# Создаёт kind-кластер и деплоит weather-pipeline в dev-оверлей.
# Требования: kind, kubectl, docker

set -euo pipefail

CLUSTER_NAME="weather-pipeline"
NAMESPACE="weather-pipeline"

echo "=== Checking dependencies ==="
for cmd in kind kubectl docker; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: $cmd not found. Please install it."
    exit 1
  fi
done

echo "=== Creating kind cluster ==="
if kind get clusters | grep -q "$CLUSTER_NAME"; then
  echo "Cluster '$CLUSTER_NAME' already exists, skipping."
else
  kind create cluster --config k8s/kind-config.yaml
fi

echo "=== Switching kubectl context ==="
kubectl config use-context "kind-$CLUSTER_NAME"

echo "=== Building Docker images ==="
docker build -t weather-mock:latest     ./mock-owm
docker build -t weather-collector:latest ./go-collector
docker build -t weather-arrow:latest    ./arrow-server

echo "=== Loading images into kind ==="
kind load docker-image weather-mock:latest \
    --name "$CLUSTER_NAME"
kind load docker-image weather-collector:latest \
    --name "$CLUSTER_NAME"
kind load docker-image weather-arrow:latest \
    --name "$CLUSTER_NAME"

echo "=== Deploying to dev overlay ==="
kubectl apply -k k8s/overlays/dev/

echo "=== Waiting for pods ==="
kubectl wait --for=condition=available \
    --timeout=120s \
    deployment/dev-mock-owm \
    -n "$NAMESPACE" || true

kubectl wait --for=condition=available \
    --timeout=120s \
    deployment/dev-go-collector \
    -n "$NAMESPACE" || true

echo "=== Pod status ==="
kubectl get pods -n "$NAMESPACE"

echo "=== HPA status ==="
kubectl get hpa -n "$NAMESPACE"

echo ""
echo "=== Setup complete! ==="
echo "Watch pods: kubectl get pods -n $NAMESPACE -w"
echo "Watch HPA:  kubectl get hpa -n $NAMESPACE -w"
echo "Logs:       kubectl logs -n $NAMESPACE -l app=go-collector -f"
