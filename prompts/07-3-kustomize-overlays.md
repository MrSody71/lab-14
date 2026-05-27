Прочитай CLAUDE.md. Создай kustomize-оверлеи для dev (kind/minikube) и prod окружений.

## Структура

```
k8s/
  overlays/
    dev/
      kustomization.yaml
      collector-patch.yaml      # replicas, HPA limits
      resources-patch.yaml      # resource requests/limits
      configmap-patch.yaml      # env-специфичные переменные
    prod/
      kustomization.yaml
      collector-patch.yaml
      resources-patch.yaml
      configmap-patch.yaml
```

## Dev оверлей

`k8s/overlays/dev/kustomization.yaml`:
- `namePrefix: dev-`
- `bases: [../../base]`
- patches: collector-patch, resources-patch, configmap-patch
- images: weather-collector:latest, weather-arrow:latest, weather-mock:latest

`k8s/overlays/dev/collector-patch.yaml`:
- Deployment go-collector: replicas: 1
- HPA go-collector-hpa: maxReplicas: 3

`k8s/overlays/dev/resources-patch.yaml`:
- container collector: requests cpu:50m memory:32Mi, limits cpu:200m memory:128Mi

`k8s/overlays/dev/configmap-patch.yaml`:
- POLL_INTERVAL_SEC: "5"
- LOG_LEVEL: "debug"
- TOTAL_SHARDS: "1"

## Prod оверлей

`k8s/overlays/prod/kustomization.yaml`:
- `namePrefix: prod-`
- `bases: [../../base]`
- patches: collector-patch, resources-patch, configmap-patch
- images: weather-collector:v1.0.0, weather-arrow:v1.0.0, weather-mock:v1.0.0

`k8s/overlays/prod/collector-patch.yaml`:
- Deployment go-collector: replicas: 3
- HPA go-collector-hpa: minReplicas: 2, maxReplicas: 10
- scaleUp: stabilizationWindowSeconds: 15, policy Pods value:2 periodSeconds:30

`k8s/overlays/prod/resources-patch.yaml`:
- container collector: requests cpu:200m memory:128Mi, limits cpu:1000m memory:512Mi

`k8s/overlays/prod/configmap-patch.yaml`:
- POLL_INTERVAL_SEC: "10"
- LOG_LEVEL: "warn"
- BATCH_SIZE: "100"

## ПРОВЕРКА

```
python3 -c "
import yaml, glob
for f in glob.glob('k8s/**/*.yaml', recursive=True):
    list(yaml.safe_load_all(open(f).read()))
    print(f'OK: {f}')
"
```

prompts/07-3-kustomize-overlays.md — этот промт целиком.
