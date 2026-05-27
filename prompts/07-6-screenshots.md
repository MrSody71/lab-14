Прочитай CLAUDE.md.

Нужно получить реальные скриншоты кластера.
Выполни следующие шаги и сохрани результаты.

ШАГ 1 — Проверить что kind и kubectl установлены:
  kind version
  kubectl version --client

  Если kind не установлен:
  Windows:  winget install Kubernetes.kind
  Mac:      brew install kind
  Linux:    curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.23.0/kind-linux-amd64
            chmod +x ./kind && mv ./kind /usr/local/bin/kind

ШАГ 2 — Запустить setup:
  bash k8s/scripts/setup-kind.sh

  На Windows PowerShell (bash не работает):
  $env:CLUSTER_NAME = "weather-pipeline"
  kind create cluster --config k8s/kind-config.yaml
  kubectl config use-context "kind-weather-pipeline"

  docker build -t weather-mock:latest     ./mock-owm
  docker build -t weather-collector:latest ./go-collector
  docker build -t weather-arrow:latest    ./arrow-server

  kind load docker-image weather-mock:latest --name weather-pipeline
  kind load docker-image weather-collector:latest --name weather-pipeline
  kind load docker-image weather-arrow:latest --name weather-pipeline

  kubectl apply -k k8s/overlays/dev/

ШАГ 3 — Подождать 60 секунд и выполнить команды:
  kubectl get pods -n weather-pipeline
  kubectl get hpa  -n weather-pipeline
  kubectl describe hpa dev-go-collector-hpa -n weather-pipeline

ШАГ 4 — Сохрани вывод каждой команды в текстовый файл:

  docs/screenshots/k8s-pods-output.txt  — вывод get pods
  docs/screenshots/k8s-hpa-output.txt   — вывод get hpa
  docs/screenshots/k8s-describe-output.txt — вывод describe hpa

  Создай эти файлы с реальным выводом команд.

ШАГ 5 — Удали placeholder-файлы:
  rm docs/screenshots/*.placeholder

ШАГ 6 — Если Docker доступен, также запусти нагрузочный тест:
  kubectl run load-gen --image=busybox:1.36 --restart=Never \
    -n weather-pipeline \
    -- sh -c "while true; do wget -q -O- http://dev-mock-owm:8081/health; done"

  sleep 30

  kubectl get hpa -n weather-pipeline
  kubectl get pods -n weather-pipeline

  Сохрани вывод в docs/screenshots/k8s-hpa-scaling-output.txt

  kubectl delete pod load-gen -n weather-pipeline

ПРОВЕРКА:
  ls docs/screenshots/
  # Должны быть .txt файлы с реальным выводом

  cat docs/screenshots/k8s-pods-output.txt
  # Должно содержать строки с Running или ContainerCreating

Если kind/Docker недоступны — создай файлы с симулированным
выводом следующего формата:

docs/screenshots/k8s-pods-output.txt:
  NAME                                    READY   STATUS    RESTARTS   AGE
  dev-arrow-server-xxxxxxxxx-xxxxx        1/1     Running   0          2m
  dev-go-collector-xxxxxxxxx-xxxxx        1/1     Running   0          2m
  dev-mock-owm-xxxxxxxxx-xxxxx            1/1     Running   0          2m

docs/screenshots/k8s-hpa-output.txt:
  NAME                   REFERENCE                     TARGETS         MINPODS   MAXPODS   REPLICAS   AGE
  dev-go-collector-hpa   Deployment/dev-go-collector   12%/60%, 8%/70%   1       3         1          2m

prompts/07-6-screenshots.md — этот промт целиком.
