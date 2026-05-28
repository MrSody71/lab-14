Создай базовые Kubernetes-манифесты в k8s/base/.
Это общие ресурсы для всех окружений (dev и prod).

=== k8s/base/namespace.yaml ===

apiVersion: v1
kind: Namespace
metadata:
  name: weather-pipeline
  labels:
    app.kubernetes.io/name: weather-pipeline
    app.kubernetes.io/managed-by: kustomize

=== k8s/base/configmap.yaml ===

apiVersion: v1
kind: ConfigMap
metadata:
  name: weather-config
  namespace: weather-pipeline
data:
  CITIES: >-
    Moscow,Saint-Petersburg,Novosibirsk,Yekaterinburg,
    Kazan,Stockholm,Berlin,London,New-York,Tokyo
  POLL_INTERVAL_SEC: "10"
  WINDOW_SIZE_SEC: "60"
  KAFKA_TOPIC: "weather.raw"
  NATS_SUBJECT: "weather.raw"
  ARROW_FLIGHT_ADDR: ":8815"
  LOG_LEVEL: "info"
  BATCH_SIZE: "50"

=== k8s/base/secret.yaml ===

# Заглушка — в реальном деплое использовать Sealed Secrets
# или внешний менеджер секретов.
# Значения — base64("placeholder")
apiVersion: v1
kind: Secret
metadata:
  name: weather-secrets
  namespace: weather-pipeline
  annotations:
    # ВАЖНО: замените на реальные значения перед деплоем
    note: "placeholder values — replace before production deploy"
type: Opaque
data:
  OWM_API_KEY: <base64-encoded-placeholder>

=== k8s/base/mock-owm-deployment.yaml ===

apiVersion: apps/v1
kind: Deployment
metadata:
  name: mock-owm
  namespace: weather-pipeline
  labels:
    app: mock-owm
    app.kubernetes.io/component: mock
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mock-owm
  template:
    metadata:
      labels:
        app: mock-owm
    spec:
      containers:
        - name: mock-owm
          image: weather-mock:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8081
              name: http
          env:
            - name: MOCK_OWM_ADDR
              value: ":8081"
            - name: MOCK_OWM_SEED
              value: "42"
          resources:
            requests:
              cpu: "50m"
              memory: "32Mi"
            limits:
              cpu: "200m"
              memory: "64Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8081
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health
              port: 8081
            initialDelaySeconds: 3
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: mock-owm
  namespace: weather-pipeline
spec:
  selector:
    app: mock-owm
  ports:
    - port: 8081
      targetPort: 8081
      name: http
  type: ClusterIP

=== k8s/base/collector-deployment.yaml ===

apiVersion: apps/v1
kind: Deployment
metadata:
  name: go-collector
  namespace: weather-pipeline
  labels:
    app: go-collector
    app.kubernetes.io/component: collector
spec:
  replicas: 2
  selector:
    matchLabels:
      app: go-collector
  template:
    metadata:
      labels:
        app: go-collector
      annotations:
        # Prometheus scrape (для HPA по custom metrics)
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      containers:
        - name: collector
          image: weather-collector:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8080
              name: metrics
          envFrom:
            - configMapRef:
                name: weather-config
          env:
            - name: OWM_MOCK_URL
              value: "http://mock-owm:8081"
            - name: ETCD_ENDPOINTS
              value: "etcd:2379"
            - name: KAFKA_BROKERS
              value: "redpanda:9093"
            - name: NATS_URL
              value: "nats://nats:4222"
            - name: SHARD_ID
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: TOTAL_SHARDS
              value: "2"
          resources:
            requests:
              cpu: "100m"
              memory: "64Mi"
            limits:
              cpu: "500m"
              memory: "256Mi"
          livenessProbe:
            exec:
              command: ["/bin/sh", "-c", "exit 0"]
            initialDelaySeconds: 10
            periodSeconds: 30
      terminationGracePeriodSeconds: 30

=== k8s/base/collector-hpa.yaml ===

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: go-collector-hpa
  namespace: weather-pipeline
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: go-collector
  minReplicas: 1
  maxReplicas: 5
  metrics:
    # Масштабирование по CPU
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
    # Масштабирование по памяти
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
        - type: Pods
          value: 1
          periodSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 120
      policies:
        - type: Pods
          value: 1
          periodSeconds: 60

=== k8s/base/arrow-server-deployment.yaml ===

apiVersion: apps/v1
kind: Deployment
metadata:
  name: arrow-server
  namespace: weather-pipeline
  labels:
    app: arrow-server
    app.kubernetes.io/component: arrow
spec:
  replicas: 1
  selector:
    matchLabels:
      app: arrow-server
  template:
    metadata:
      labels:
        app: arrow-server
    spec:
      containers:
        - name: arrowsrv
          image: weather-arrow:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8815
              name: flight
          envFrom:
            - configMapRef:
                name: weather-config
          env:
            - name: KAFKA_BROKERS
              value: "redpanda:9093"
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          readinessProbe:
            tcpSocket:
              port: 8815
            initialDelaySeconds: 5
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: arrow-server
  namespace: weather-pipeline
spec:
  selector:
    app: arrow-server
  ports:
    - port: 8815
      targetPort: 8815
      name: flight
  type: ClusterIP

=== k8s/base/kustomization.yaml ===

apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: weather-pipeline

resources:
  - namespace.yaml
  - configmap.yaml
  - secret.yaml
  - mock-owm-deployment.yaml
  - collector-deployment.yaml
  - collector-hpa.yaml
  - arrow-server-deployment.yaml

commonLabels:
  app.kubernetes.io/part-of: weather-pipeline
  app.kubernetes.io/version: "0.1.0"

ПРОВЕРКА:
  # Валидация YAML без применения
  kubectl apply --dry-run=client -k k8s/base/ 2>&1

  Если kubectl недоступен — используй:
  python3 -c "
  import yaml, glob
  for f in glob.glob('k8s/base/*.yaml'):
      yaml.safe_load_all(open(f).read())
      print(f'OK: {f}')
  "

Все файлы должны пройти валидацию.

prompts/07-2-k8s-base.md — этот промт целиком.
