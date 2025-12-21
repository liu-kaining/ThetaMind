# 股票代码数据初始化指南

## 问题

迁移只创建了 `stock_symbols` 表结构，但没有填充数据。需要手动同步股票代码数据。

## 检查当前状态

### 1. 查看 stock_symbols 表是否为空

```bash
# 在服务器上
docker compose exec db psql -U thetamind -d thetamind -c "SELECT COUNT(*) FROM stock_symbols;"
```

### 2. 查看前几条记录（如果有）

```bash
docker compose exec db psql -U thetamind -d thetamind -c "SELECT symbol, name, is_active FROM stock_symbols LIMIT 10;"
```

## 同步股票代码

### 方法 1：使用 sync_symbols.py 脚本（推荐）

这个脚本会：
- 尝试从 Tiger API 获取股票代码
- 如果失败，使用内置的常用股票列表（包含数百个热门股票）
- 批量插入到数据库

```bash
# 在服务器上
docker compose exec backend python scripts/sync_symbols.py
```

### 方法 2：使用 sync_liquid_symbols.py（从市场扫描器获取）

这个脚本会：
- 使用 Tiger API 的市场扫描器获取流动性好的股票
- 只同步当前活跃的股票
- 将其他股票标记为非活跃

```bash
docker compose exec backend python scripts/sync_liquid_symbols.py
```

## 验证同步结果

### 1. 使用 check_symbols.py 脚本

```bash
docker compose exec backend python scripts/check_symbols.py
```

这会显示：
- 总股票数量
- 活跃股票数量
- 前 10 条记录示例

### 2. 直接查询数据库

```bash
# 查看总数
docker compose exec db psql -U thetamind -d thetamind -c "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE is_active = true) as active FROM stock_symbols;"

# 查看一些示例
docker compose exec db psql -U thetamind -d thetamind -c "SELECT symbol, name FROM stock_symbols WHERE is_active = true LIMIT 20;"
```

## 推荐流程

### 首次设置

```bash
# 1. 同步常用股票代码（包含数百个热门股票）
docker compose exec backend python scripts/sync_symbols.py

# 2. 验证
docker compose exec backend python scripts/check_symbols.py
```

### 定期更新（可选）

如果需要保持股票列表最新，可以定期运行：

```bash
# 同步流动性好的股票（从市场扫描器）
docker compose exec backend python scripts/sync_liquid_symbols.py
```

## 内置股票列表

`sync_symbols.py` 脚本包含了一个扩展的股票列表（`EXTENDED_SYMBOLS`），包括：

- **热门科技股**：AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA 等
- **金融股**：JPM, BAC, GS, MS 等
- **消费品**：NKE, SBUX, MCD 等
- **医疗**：JNJ, PFE, UNH 等
- **能源**：XOM, CVX 等
- **其他行业龙头**：数百个股票

即使 Tiger API 不可用，这个列表也能提供足够的基础股票代码供搜索和选择。

## 故障排查

### 问题 1：脚本运行失败

```bash
# 查看详细错误
docker compose exec backend python scripts/sync_symbols.py 2>&1
```

### 问题 2：Tiger API 不可用

脚本会自动使用内置列表，无需担心。

### 问题 3：想手动添加股票代码

```bash
# 进入数据库
docker compose exec db psql -U thetamind -d thetamind

# 插入股票代码
INSERT INTO stock_symbols (symbol, name, market, is_active, created_at, updated_at)
VALUES ('AAPL', 'Apple Inc.', 'US', true, NOW(), NOW())
ON CONFLICT (symbol) DO UPDATE SET name = EXCLUDED.name, is_active = true;

# 退出
\q
```

## 相关脚本说明

| 脚本 | 用途 | 数据源 |
|------|------|--------|
| `sync_symbols.py` | 同步常用股票代码 | Tiger API + 内置列表 |
| `sync_liquid_symbols.py` | 同步流动性好的股票 | Tiger 市场扫描器 |
| `check_symbols.py` | 检查股票代码数量 | 数据库查询 |
| `verify_synced_symbols.py` | 验证同步的股票代码 | 数据库查询 |

