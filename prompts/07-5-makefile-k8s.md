Прочитай CLAUDE.md.

Обнови Makefile — замени заглушки k8s-up и k8s-down
на реальные команды.

Найди в Makefile строки:
  k8s-up:
    @echo "TODO: implemented in stage 7"

  k8s-down:
    @echo "TODO: implemented in stage 7"

Замени на:

k8s-up: ## Создать kind-кластер и задеплоить dev-оверлей
    bash k8s/scripts/setup-kind.sh

k8s-down: ## Удалить kind-кластер
    bash k8s/scripts/teardown-kind.sh

k8s-status: ## Состояние подов и HPA
    kubectl get all -n weather-pipeline
    kubectl get hpa -n weather-pipeline

k8s-logs: ## Логи go-collector
    kubectl logs -n weather-pipeline -l app=go-collector -f

k8s-load-test: ## Нагрузочный тест для проверки HPA
    bash k8s/scripts/load-test.sh

k8s-diff: ## Посмотреть diff без применения
    kubectl diff -k k8s/overlays/dev/ || true

Добавь эти цели в .PHONY в конце Makefile.

Обнови раздел ## Kubernetes в корневом README.md —
замени "TODO" на реальные команды:

```bash
# Создать кластер и задеплоить
make k8s-up

# Посмотреть состояние
make k8s-status

# Наблюдать за HPA
kubectl get hpa -n weather-pipeline -w

# Нагрузочный тест
make k8s-load-test

# Удалить кластер
make k8s-down
```

И добавь ссылку: "Подробнее: [docs/kubernetes.md](docs/kubernetes.md)"

ПРОВЕРКА:
  make help | grep k8s
  # Должно показать 5-6 k8s-* целей

  grep -c "k8s" Makefile
  # Должно быть >= 10 строк с k8s

prompts/07-5-makefile-k8s.md — этот промт целиком.
