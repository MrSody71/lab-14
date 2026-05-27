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
