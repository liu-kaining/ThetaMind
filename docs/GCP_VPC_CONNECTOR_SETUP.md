# GCP VPC Connector 设置指南

## 为什么需要 VPC Connector？

Cloud Run 是 Serverless 服务，默认在 Google 管理的网络中运行。Memorystore (Redis) 只有**内网 IP**，Cloud Run 无法直接访问。

**解决方案**：使用 Serverless VPC Access Connector 让 Cloud Run 访问 VPC 内的资源（如 Memorystore Redis）。

## 创建 VPC Connector

### 方法 1：使用 GCP 控制台

1. 打开 [Serverless VPC Access](https://console.cloud.google.com/networking/connectors) 页面
2. 点击 "**创建连接器**" (Create Connector)
3. 填写配置：
   - **名称**：`thetamind-vpc-connector`
   - **区域**：`us-central1`（必须与 Cloud Run 服务在同一区域）
   - **网络**：`default`（或你的自定义 VPC 网络）
   - **子网**：选择或创建一个子网
   - **最小实例数**：`2`（推荐，确保高可用）
   - **最大实例数**：`3`
   - **机器类型**：`f1-micro`（最便宜的选项）

4. 点击 "**创建**"

### 方法 2：使用 gcloud CLI

```bash
# 设置变量
PROJECT_ID="your-project-id"
REGION="us-central1"
CONNECTOR_NAME="thetamind-vpc-connector"
NETWORK="default"  # 或你的 VPC 网络名称

# 创建连接器
gcloud compute networks vpc-access connectors create $CONNECTOR_NAME \
  --region=$REGION \
  --network=$NETWORK \
  --range=10.8.0.0/28 \
  --min-instances=2 \
  --max-instances=3 \
  --machine-type=f1-micro \
  --project=$PROJECT_ID
```

**注意**：
- `--range` 指定了连接器使用的 IP 地址范围（CIDR 格式）
- 确保这个范围不与你的 VPC 子网冲突
- 最小推荐范围：`/28`（16 个 IP 地址）

### 验证连接器创建

```bash
gcloud compute networks vpc-access connectors describe $CONNECTOR_NAME \
  --region=$REGION \
  --project=$PROJECT_ID
```

应该看到状态为 `READY`。

## 在 Cloud Run 中使用 VPC Connector

VPC Connector 已经在 `cloudbuild.yaml` 中配置：

```yaml
- '--vpc-connector'
- 'thetamind-vpc-connector'
```

## 成本说明

- **f1-micro 实例**：按运行时间计费，最小实例数为 2
- **估算成本**：约 $10-15/月（取决于使用量）
- **建议**：如果不使用 Redis 缓存，可以暂时不创建 VPC Connector，应用会以降级模式运行（无缓存）

## 故障排查

### 问题：连接器创建失败

**可能原因**：
1. IP 范围与现有子网冲突
2. 区域选择错误（必须与 Cloud Run 相同）
3. 权限不足

**解决方法**：
- 检查 IP 范围是否可用：`gcloud compute networks subnets list`
- 确保使用正确的区域
- 检查 IAM 权限：`roles/vpcaccess.admin`

### 问题：Cloud Run 无法连接到 Redis

**可能原因**：
1. VPC Connector 未正确配置
2. Redis 防火墙规则阻止了连接

**解决方法**：
- 检查 Cloud Run 服务日志
- 验证 VPC Connector 状态：`READY`
- 检查 Redis 的授权网络配置

## 相关文档

- [Serverless VPC Access 官方文档](https://cloud.google.com/vpc/docs/configure-serverless-vpc-access)
- [Cloud Run 网络配置](https://cloud.google.com/run/docs/configuring/connecting-vpc)

