# MCP Maximo Server

遠端 MCP (Model Context Protocol) 伺服器，將 IBM Maximo API 服務包裝為 MCP Tools，供 Dify Agent 等 AI 應用程式使用。

## 功能特點

### 支援的 Maximo 功能

#### 資產管理 (Asset Management)
- `get_asset` - 查詢資產詳細資訊
- `search_assets` - 搜尋資產（支援多種篩選條件）
- `create_asset` - 建立新資產
- `update_asset_status` - 更新資產狀態

#### 工單管理 (Work Order Management)
- `get_work_order` - 查詢工單詳細資訊
- `search_work_orders` - 搜尋工單
- `create_work_order` - 建立新工單
- `update_work_order_status` - 更新工單狀態

#### 庫存管理 (Inventory Management)
- `get_inventory` - 查詢庫存項目
- `search_inventory` - 搜尋庫存（支援低庫存篩選）
- `issue_inventory` - 發料作業

### 架構特性

- ✅ **FastMCP 框架** - 使用官方 MCP SDK
- ✅ **HTTP + SSE 傳輸** - 符合 MCP 2025 標準
- ✅ **API Key 雙層認證** - Dify→MCP 及 MCP→Maximo
- ✅ **Redis 快取** - 降低 Maximo 負載，提升效能
- ✅ **速率限制** - Token Bucket 演算法保護系統
- ✅ **結構化日誌** - JSON 格式，含 Correlation ID
- ✅ **連接池** - HTTP 連接重用，優化效能
- ✅ **重試機制** - 自動重試暫時性錯誤
- ✅ **健康檢查** - 監控 Maximo 和 Redis 連接狀態
- ✅ **Docker 容器化** - 易於部署和擴展

## 快速開始

### 前置需求

- Docker & Docker Compose
- Maximo API Key（在 Maximo 中生成）
- 安全的 MCP API Key（用於 Dify 連接）

### 1. 複製專案

```bash
git clone <repository-url>
cd mcp-maximo-server
```

### 2. 配置環境變數

```bash
cp .env.example .env
```

編輯 `.env` 檔案，設定以下必要參數：

```env
# MCP 認證
MCP_API_KEY=your-secure-mcp-api-key-here

# Maximo 設定
MAXIMO_API_URL=https://maximo.yourcompany.com/maximo
MAXIMO_API_KEY=your-maximo-api-key-here
```

### 3. 啟動服務

```bash
docker-compose up -d
```

### 4. 驗證服務

檢查健康狀態：

```bash
curl http://localhost:8000/health
```

預期回應：

```json
{
  "status": "healthy",
  "cache": "healthy",
  "maximo": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

## Dify 整合

### 在 Dify 中配置 MCP Server

1. 開啟 Dify 設定
2. 新增 MCP Server 連接
3. 使用以下配置：

```json
{
  "maximo_server": {
    "url": "http://your-server-host:8000/mcp/sse",
    "headers": {
      "Authorization": "Bearer YOUR_MCP_API_KEY"
    },
    "timeout": 30
  }
}
```

### 在 Dify Agent 中使用

MCP Tools 會自動出現在 Dify Agent 的工具列表中：

- 資產管理工具（4 個）
- 工單管理工具（4 個）
- 庫存管理工具（3 個）

## API 文件

### 可用的 MCP Tools

#### 資產管理

**get_asset**
```python
get_asset(assetnum="PUMP001", siteid="BEDFORD")
```

**search_assets**
```python
search_assets(
    query="pump",
    status="OPERATING",
    location="BLDG-100"
)
```

**create_asset**
```python
create_asset(
    assetnum="PUMP123",
    siteid="BEDFORD",
    description="新的水泵設備",
    assettype="PUMP",
    location="BLDG-100"
)
```

**update_asset_status**
```python
update_asset_status(
    assetnum="PUMP001",
    siteid="BEDFORD",
    new_status="OPERATING",
    memo="設備已完成維護"
)
```

#### 工單管理

**get_work_order**
```python
get_work_order(wonum="WO1001", siteid="BEDFORD")
```

**search_work_orders**
```python
search_work_orders(
    status="WAPPR",
    worktype="PM",
    assetnum="PUMP001"
)
```

**create_work_order**
```python
create_work_order(
    description="例行維護",
    siteid="BEDFORD",
    assetnum="PUMP001",
    worktype="PM",
    priority=2
)
```

**update_work_order_status**
```python
update_work_order_status(
    wonum="WO1001",
    siteid="BEDFORD",
    new_status="INPRG"
)
```

#### 庫存管理

**get_inventory**
```python
get_inventory(
    itemnum="FILTER-001",
    siteid="BEDFORD",
    location="STOREROOM"
)
```

**search_inventory**
```python
search_inventory(
    query="filter",
    low_stock=True,
    siteid="BEDFORD"
)
```

**issue_inventory**
```python
issue_inventory(
    itemnum="FILTER-001",
    quantity=5,
    siteid="BEDFORD",
    location="STOREROOM",
    to_wonum="WO1001"
)
```

## 效能調校

### 快取設定

在 `.env` 中調整快取 TTL：

```env
CACHE_TTL_ASSET=600        # 資產快取 10 分鐘
CACHE_TTL_WORKORDER=300    # 工單快取 5 分鐘
CACHE_TTL_INVENTORY=600    # 庫存快取 10 分鐘
```

### 速率限制

調整速率限制以符合您的需求：

```env
RATE_LIMIT_PER_MINUTE=100           # 一般請求
RATE_LIMIT_SEARCH_PER_MINUTE=50     # 搜尋請求
RATE_LIMIT_CREATE_PER_MINUTE=20     # 建立請求
```

## 監控與日誌

### 查看日誌

```bash
# 即時日誌
docker-compose logs -f mcp-server

# 查看特定數量的日誌
docker-compose logs --tail=100 mcp-server
```

### 結構化日誌格式

日誌以 JSON 格式輸出，包含以下欄位：

- `timestamp` - ISO 8601 時間戳
- `correlation_id` - 請求追蹤 ID
- `level` - 日誌等級
- `message` - 日誌訊息
- `app` - 應用程式名稱
- `version` - 版本號

範例：

```json
{
  "timestamp": "2025-01-06T10:30:00Z",
  "correlation_id": "abc-123",
  "level": "INFO",
  "message": "Maximo GET success",
  "url": "/oslc/os/mxapiasset",
  "status_code": 200,
  "duration_ms": 245
}
```

## 部署選項

### Docker Compose（本地/開發）

```bash
docker-compose up -d
```

### Google Cloud Run

```bash
# 建置並推送映像
docker build -t gcr.io/your-project/mcp-maximo-server .
docker push gcr.io/your-project/mcp-maximo-server

# 部署到 Cloud Run
gcloud run deploy mcp-maximo-server \
  --image gcr.io/your-project/mcp-maximo-server \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Azure App Service

```bash
# 使用 Azure CLI
az webapp create --resource-group myResourceGroup \
  --plan myAppServicePlan \
  --name mcp-maximo-server \
  --deployment-container-image-name your-registry/mcp-maximo-server:latest
```

## 故障排除

### 連接 Maximo 失敗

檢查：
1. `MAXIMO_API_URL` 是否正確
2. `MAXIMO_API_KEY` 是否有效
3. 防火牆規則是否允許連接
4. Maximo API 是否啟用

### Redis 連接失敗

檢查：
1. Redis 容器是否運行：`docker-compose ps`
2. Redis 健康檢查：`docker-compose exec redis redis-cli ping`
3. 網路連接：確保容器在同一網路中

### Dify 無法連接

檢查：
1. MCP Server URL 是否正確
2. `MCP_API_KEY` 在 `.env` 和 Dify 配置中是否一致
3. 使用 `/health` 端點驗證服務可用性

## 安全建議

1. **使用強 API Key** - 使用 `openssl rand -hex 32` 生成
2. **啟用 HTTPS** - 在生產環境使用 TLS
3. **定期輪換密鑰** - 每 60-90 天輪換 API Keys
4. **限制 CORS** - 設定特定的允許來源
5. **使用 Secrets Manager** - 不要在環境變數中存放敏感資訊（生產環境）

## 專案結構

```
mcp-maximo-server/
├── src/
│   ├── main.py                 # FastMCP 應用程式主檔案
│   ├── config.py               # 配置管理
│   ├── auth/
│   │   └── api_key.py          # API Key 認證
│   ├── clients/
│   │   └── maximo_client.py    # Maximo API 客戶端
│   ├── tools/
│   │   ├── asset_tools.py      # 資產管理工具
│   │   ├── workorder_tools.py  # 工單管理工具
│   │   └── inventory_tools.py  # 庫存管理工具
│   ├── middleware/
│   │   ├── cache.py            # Redis 快取
│   │   └── rate_limiter.py     # 速率限制
│   └── utils/
│       └── logger.py           # 結構化日誌
├── Dockerfile                  # Docker 映像定義
├── docker-compose.yml          # Docker Compose 配置
├── requirements.txt            # Python 依賴套件
├── .env.example                # 環境變數範例
└── README.md                   # 本檔案
```

## 授權

[指定您的授權]

## 支援

如有問題或需要協助，請：
1. 查看本文件的故障排除部分
2. 檢查健康檢查端點：`/health`
3. 查看應用程式日誌
4. 聯繫技術支援團隊
