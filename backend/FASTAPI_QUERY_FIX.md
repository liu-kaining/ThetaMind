# FastAPI Query 参数默认值修复

## 🔴 错误

```
AssertionError: `Query` default value cannot be set in `Annotated` for 'period_length'. 
Set the default value with `=` instead.
```

## ❌ 错误写法

```python
# ❌ 错误：不能在 Query() 中设置 default，同时在参数中也有 =
period_length: Annotated[int, Query(default=10, ge=1, le=200)] = 10
```

## ✅ 正确写法

```python
# ✅ 正确：只在参数定义中使用 = 设置默认值
period_length: Annotated[int, Query(ge=1, le=200, description="...")] = 10
```

## 📝 修复内容

已修复以下函数中的 Query 参数：

1. `get_technical_indicator()`:
   - `period_length`: 移除 `Query(default=10)`，保留 `= 10`
   - `timeframe`: 移除 `Query(default="1day")`，保留 `= "1day"`

2. `get_industry_performance()`:
   - `date`: 移除 `Query(default=None)`，保留 `= None`

3. `get_earnings_estimates()`:
   - `period`: 移除 `Query(default="annual")`，保留 `= "annual"`
   - `limit`: 移除 `Query(default=10)`，保留 `= 10`

## 🚀 重新启动

```bash
docker-compose restart backend
# 或
docker-compose up -d --build backend
```

## ✅ 验证

启动后应该不再看到 `AssertionError`，backend 应该正常启动。
