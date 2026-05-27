#!/usr/bin/env bash
# Нагрузочный тест для проверки HPA:
# генерирует CPU-нагрузку и смотрит как HPA масштабирует поды.
set -euo pipefail

NAMESPACE="weather-pipeline"
DEPLOYMENT="dev-go-collector"

echo "=== Current state ==="
kubectl get hpa -n "$NAMESPACE"
kubectl get pods -n "$NAMESPACE" -l app=go-collector

echo ""
echo "=== Running load test (60 seconds) ==="
echo "Watch HPA in another terminal:"
echo "  kubectl get hpa -n $NAMESPACE -w"
echo ""

# Запускаем временный pod с нагрузкой на CPU
kubectl run load-generator \
    --image=busybox:1.36 \
    --restart=Never \
    --namespace="$NAMESPACE" \
    -- sh -c "
        while true; do
            wget -q -O- \
                http://dev-mock-owm:8081/batch?cities=Moscow,London,Tokyo \
                > /dev/null 2>&1
        done
    " || true

echo "Load generator started. Waiting 60s..."
sleep 60

echo "=== HPA status after load ==="
kubectl get hpa -n "$NAMESPACE"
kubectl get pods -n "$NAMESPACE" -l app=go-collector

echo "=== Stopping load generator ==="
kubectl delete pod load-generator -n "$NAMESPACE" --ignore-not-found
