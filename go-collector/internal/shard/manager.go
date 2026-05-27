package shard

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"time"

	clientv3 "go.etcd.io/etcd/client/v3"
)

const (
	shardPrefix = "/weather-pipeline/shards/"
	leaseTTL    = 15 // секунд
)

// Manager handles shard registration and city assignment via etcd.
type Manager struct {
	client  *clientv3.Client
	shardID string
	cities  []string
	logger  *slog.Logger
}

// ShardInfo is stored in etcd under shardPrefix+shardID.
type ShardInfo struct {
	ShardID      string    `json:"shard_id"`
	RegisteredAt time.Time `json:"registered_at"`
}

// NewManager creates a Manager and connects to etcd.
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

// Register registers this shard in etcd with a lease and keep-alive.
// Blocks until ctx is cancelled — run in a goroutine.
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

	ch, err := m.client.KeepAlive(ctx, lease.ID)
	if err != nil {
		return fmt.Errorf("keepalive: %w", err)
	}
	for {
		select {
		case <-ctx.Done():
			m.logger.Info("shard unregistering", "shard_id", m.shardID)
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

// MyCities returns the cities assigned to this shard based on live shards in etcd.
func (m *Manager) MyCities(ctx context.Context) ([]string, error) {
	resp, err := m.client.Get(ctx, shardPrefix, clientv3.WithPrefix())
	if err != nil {
		return nil, fmt.Errorf("get shards: %w", err)
	}

	shardIDs := make([]string, 0, len(resp.Kvs))
	for _, kv := range resp.Kvs {
		var info ShardInfo
		if err := json.Unmarshal(kv.Value, &info); err == nil {
			shardIDs = append(shardIDs, info.ShardID)
		}
	}
	if len(shardIDs) == 0 {
		return m.cities, nil
	}

	myCities := assignCities(shardIDs, m.shardID, m.cities)
	m.logger.Info("cities assigned",
		"shard_id", m.shardID,
		"total_shards", len(shardIDs),
		"my_cities", len(myCities))
	return myCities, nil
}

// Close closes the etcd client.
func (m *Manager) Close() error {
	return m.client.Close()
}
