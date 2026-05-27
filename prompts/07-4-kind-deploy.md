Прочитай CLAUDE.md.

Создай скрипты для развёртывания в kind (Kubernetes in Docker)
и документацию с командами.

=== k8s/kind-config.yaml ===

# Конфигурация kind-кластера для локальной разработки.
# Один control-plane + два worker узла.
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: weather-pipeline
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
    extraPortMappings:
      - containerPort: 30080
        hostPort: 30080
        protocol: TCP
      - containerPort: 30815
        hostPort: 30815
        protocol: TCP
  - role: worker
    labels:
      workload: collector
  - role: worker
    labels:
      workload: analytics

=== k8s/scripts/setup-kind.sh ===

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

=== k8s/scripts/teardown-kind.sh ===

#!/usr/bin/env bash
set -euo pipefail
echo "=== Deleting kind cluster ==="
kind delete cluster --name weather-pipeline
echo "Done."

=== k8s/scripts/load-test.sh ===

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

chmod +x k8s/scripts/*.sh

=== docs/kubernetes.md ===

# Развёртывание в Kubernetes

## Требования

- [kind](https://kind.sigs.k8s.io/) v0.23+
- kubectl v1.30+
- Docker Desktop или Docker Engine
- 4GB RAM свободно для кластера

## Быстрый старт (kind)

```bash
# 1. Создать кластер и задеплоить
bash k8s/scripts/setup-kind.sh

# 2. Проверить состояние
kubectl get all -n weather-pipeline

# 3. Посмотреть логи коллектора
kubectl logs -n weather-pipeline \
    -l app=go-collector -f

# 4. Наблюдать за HPA
kubectl get hpa -n weather-pipeline -w
```

## Архитектура в Kubernetes

```
┌─────────────────────────────────────────────────┐
│              Namespace: weather-pipeline         │
│                                                  │
│  ┌─────────────┐     ┌──────────────────────┐   │
│  │  mock-owm   │────▶│  go-collector (HPA)  │   │
│  │  Deployment │     │  min=1, max=5 pods   │   │
│  │  1 replica  │     │  CPU target: 60%     │   │
│  └─────────────┘     └──────────┬───────────┘   │
│                                 │               │
│                    ┌────────────▼────────────┐  │
│                    │     arrow-server         │  │
│                    │     1 replica            │  │
│                    │     port: 8815 (Flight)  │  │
│                    └─────────────────────────┘  │
│                                                  │
│  ConfigMap: weather-config                       │
│  Secret:    weather-secrets                      │
│  HPA:       go-collector-hpa                     │
└─────────────────────────────────────────────────┘
```

## Окружения

| Параметр | dev | prod |
|---|---|---|
| go-collector replicas | 1 | 3 |
| HPA max pods | 3 | 10 |
| Poll interval | 5s | 10s |
| Log level | debug | warn |
| Resource requests CPU | 50m | 200m |

## HPA — Horizontal Pod Autoscaler

HPA настроен на масштабирование по двум метрикам:

```yaml
metrics:
  - CPU utilization > 60%   → добавить pod
  - Memory utilization > 70% → добавить pod
```

Поведение:
- Scale up: +1 pod каждые 30s при нагрузке
- Scale down: -1 pod каждые 60s при снижении
- Cooldown scale up: 30s
- Cooldown scale down: 120s

## Нагрузочный тест (проверка HPA)

```bash
# Запустить нагрузку и смотреть как HPA масштабирует поды
bash k8s/scripts/load-test.sh

# В другом терминале наблюдать:
kubectl get hpa -n weather-pipeline -w
kubectl get pods -n weather-pipeline -w
```

## Оверлеи (kustomize)

```bash
# Dev (kind/minikube)
kubectl apply -k k8s/overlays/dev/

# Prod
kubectl apply -k k8s/overlays/prod/

# Посмотреть что применится без деплоя
kubectl diff -k k8s/overlays/dev/
```

## Удаление кластера

```bash
bash k8s/scripts/teardown-kind.sh
```

## Placeholder для скриншотов

После запуска в kind сделайте скриншоты и положите в
docs/screenshots/:

- `k8s-pods-running.png`  — `kubectl get pods -n weather-pipeline`
- `k8s-hpa-status.png`    — `kubectl get hpa -n weather-pipeline`
- `k8s-hpa-scaling.png`   — HPA во время нагрузочного теста

```bash
# Команды для скриншотов
kubectl get pods -n weather-pipeline
kubectl get hpa  -n weather-pipeline
kubectl describe hpa go-collector-hpa -n weather-pipeline
```

Добавь в docs/screenshots/ файлы-placeholder:
  k8s-pods-running.png.placeholder
  k8s-hpa-status.png.placeholder
  k8s-hpa-scaling.png.placeholder

(Замените на реальные скриншоты перед сдачей)

ПРОВЕРКА:
  # Валидация всех YAML
  python3 -c "
  import yaml, glob
  files = glob.glob('k8s/**/*.yaml', recursive=True)
  for f in files:
      list(yaml.safe_load_all(open(f).read()))
      print(f'OK: {f}')
  print(f'Total: {len(files)} files')
  "

  # Проверить что скрипты исполняемые
  ls -la k8s/scripts/

  # Проверить docs/kubernetes.md
  wc -l docs/kubernetes.md

prompts/07-4-kind-deploy.md — этот промт целиком.
