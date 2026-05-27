Прочитай CLAUDE.md.

Реализуй логику шардирования городов через etcd.
Идея: каждый инстанс коллектора регистрируется в etcd со своим ShardID.
Список городов делится между живыми шардами. Если шард умирает —
его города перераспределяются между оставшимися.

Добавь зависимость в go-collector/go.mod:
  go get go.etcd.io/etcd/client/v3@v3.5.15

=== go-collector/internal/shard/manager.go ===

package shard

import (
    "context"
    "encoding/json"
    "fmt"
    "log/slog"
    "sort"
    "time"

    clientv3 "go.etcd.io/etcd/client/v3"
)

const (
    shardPrefix  = "/weather-pipeline/shards/"
    leaseTTL     = 15 // секунд
)

type Manager struct {
    client   *clientv3.Client
    shardID  string
    cities   []string
    logger   *slog.Logger
}

type ShardInfo struct {
    ShardID  string    `json:"shard_id"`
    RegisteredAt time.Time `json:"registered_at"`
}

func NewManager(endpoints []string, shardID string,
    cities []string, logger *slog.Logger) (*Manager, error) {
    
    cli, err := clientv3.New(clientv3.Config{
        Endpoints:   endpoints,
        DialTimeout: 5 * time.Second,
    })
    if err != nil {
        return nil, fmt.Errorf("connect etcd: %w", err)
    }
    return &Manager{
        client:  cli,
        shardID: shardID,
        cities:  cities,
        logger:  logger,
    }, nil
}

// Register регистрирует этот шард в etcd с lease (keep-alive).
// Блокирует до отмены ctx — запускай в горутине.
func (m *Manager) Register(ctx context.Context) error {
    lease, err := m.client.Grant(ctx, leaseTTL)
    if err != nil {
        return fmt.Errorf("grant lease: %w", err)
    }

    info := ShardInfo{ShardID: m.shardID, RegisteredAt: time.Now().UTC()}
    data, _ := json.Marshal(info)

    key := shardPrefix + m.shardID
    _, err = m.client.Put(ctx, key, string(data),
        clientv3.WithLease(lease.ID))
    if err != nil {
        return fmt.Errorf("register shard: %w", err)
    }
    m.logger.Info("shard registered", "shard_id", m.shardID,
        "lease_id", lease.ID)

    // Keep-alive: обновляем lease каждые leaseTTL/3 секунд
    ch, err := m.client.KeepAlive(ctx, lease.ID)
    if err != nil {
        return fmt.Errorf("keepalive: %w", err)
    }
    for {
        select {
        case <-ctx.Done():
            m.logger.Info("shard unregistering", "shard_id", m.shardID)
            // Отзываем lease при штатном завершении
            rCtx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
            defer cancel()
            _, _ = m.client.Revoke(rCtx, lease.ID)
            return nil
        case resp, ok := <-ch:
            if !ok {
                return fmt.Errorf("keepalive channel closed")
            }
            m.logger.Debug("lease renewed", "ttl", resp.TTL)
        }
    }
}

// MyCities возвращает список городов, закреплённых за этим шардом.
// Алгоритм: получить все живые шарды из etcd, отсортировать по ShardID,
// взять города с индексами i где i % len(shards) == позиция этого шарда.
func (m *Manager) MyCities(ctx context.Context) ([]string, error) {
    resp, err := m.client.Get(ctx, shardPrefix, clientv3.WithPrefix())
    if err != nil {
        return nil, fmt.Errorf("get shards: %w", err)
    }

    // Собрать все живые ShardID
    shardIDs := make([]string, 0, len(resp.Kvs))
    for _, kv := range resp.Kvs {
        var info ShardInfo
        if err := json.Unmarshal(kv.Value, &info); err == nil {
            shardIDs = append(shardIDs, info.ShardID)
        }
    }
    if len(shardIDs) == 0 {
        // etcd недоступен или шарды ещё не зарегистрированы —
        // берём все города
        return m.cities, nil
    }

    sort.Strings(shardIDs)
    myPos := -1
    for i, id := range shardIDs {
        if id == m.shardID {
            myPos = i
            break
        }
    }
    if myPos == -1 {
        // Наш шард ещё не виден — берём все города
        return m.cities, nil
    }

    myCities := make([]string, 0)
    for i, city := range m.cities {
        if i%len(shardIDs) == myPos {
            myCities = append(myCities, city)
        }
    }
    m.logger.Info("cities assigned",
        "shard_id", m.shardID,
        "total_shards", len(shardIDs),
        "my_cities", len(myCities))
    return myCities, nil
}

// Close закрывает etcd-клиент.
func (m *Manager) Close() error {
    return m.client.Close()
}

=== go-collector/internal/shard/manager_test.go ===

TestAssignCities_SingleShard:
  Создать Manager с shardID="shard-0", cities=["A","B","C","D","E"].
  Вызвать assignCities([]string{"shard-0"}, "shard-0") — вынеси логику
  распределения в отдельную чистую функцию assignCities(shardIDs []string,
  myID string, cities []string) []string чтобы тестировать без etcd.
  При 1 шарде — должны вернуться все 5 городов.

TestAssignCities_TwoShards:
  shardIDs=["shard-0","shard-1"], myID="shard-0", cities=["A","B","C","D"]
  Результат: ["A","C"] (чётные индексы).
  myID="shard-1" → ["B","D"] (нечётные).

TestAssignCities_ThreeShards:
  shardIDs=["s0","s1","s2"], myID="s1", cities=["A","B","C","D","E","F"]
  Результат: ["B","E"] (индексы 1 и 4).

Вынеси assignCities в отдельный файл shard/assign.go (не в manager.go)
чтобы тесты не требовали etcd.

ПРОВЕРКА:
  go build ./go-collector/... 2>&1 && echo "BUILD OK"
  go test ./go-collector/internal/shard/... -v -run TestAssign -count=1 2>&1

3 теста зелёных.

prompts/02-3-etcd-shard.md — этот промт целиком.
