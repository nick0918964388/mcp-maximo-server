# MCP Maximo Server 配置指南

## 快速開始

### 1. 配置環境變量

已為您創建 `.env` 文件，請修改以下**必填**參數：

#### 必填參數

```bash
# MCP API Key - 用於 Dify Agent 連接 MCP Server
# 生成方式: openssl rand -hex 32
MCP_API_KEY=your-secure-mcp-api-key-here

# Maximo API Key - 從 Maximo 系統獲取
# 獲取方式: 登入 Maximo > Go To Applications > Users > 選擇您的用戶 > API Keys
MAXIMO_API_KEY=your-maximo-api-key-here
```

#### 已配置參數（可按需調整）

```bash
# Maximo URL
MAXIMO_API_URL=http://trs.webdw.xyz:9088/maximo

# 外部訪問端口
PORT=8001

# Redis 配置（使用 docker-compose 時）
REDIS_HOST=redis
REDIS_PORT=6379
```

### 2. 生成 MCP API Key

在終端執行：

```bash
# Windows (Git Bash 或 WSL)
openssl rand -hex 32

# 或使用 Python
python -c "import secrets; print(secrets.token_hex(32))"
```

將生成的密鑰複製到 `.env` 文件的 `MCP_API_KEY` 欄位。

### 3. 獲取 Maximo API Key

1. 登入您的 Maximo 系統
2. 前往 **Go To Applications** > **Users**
3. 選擇您的用戶帳號
4. 點擊 **API Keys** 標籤
5. 點擊 **Generate** 生成新的 API Key
6. 複製生成的 API Key 到 `.env` 文件的 `MAXIMO_API_KEY` 欄位

### 4. 啟動服務

```bash
# 停止現有容器
docker-compose down

# 重新構建並啟動（使用新的 .env 配置）
docker-compose up -d --build

# 查看日誌
docker-compose logs -f mcp-server
```

### 5. 驗證配置

打開瀏覽器訪問測試頁面：

```
http://localhost:8001
或
http://192.168.1.214:8001
```

測試頁面會顯示：
- ✅ 系統健康檢查（Cache 和 Maximo 連接狀態）
- ✅ Maximo 連接測試
- ✅ MCP Tools 功能測試
- ✅ 請求/回應日誌

## 檢查清單

- [ ] `.env` 文件中已填寫 `MCP_API_KEY`
- [ ] `.env` 文件中已填寫 `MAXIMO_API_KEY`
- [ ] `MAXIMO_API_URL` 正確指向您的 Maximo 實例
- [ ] 執行 `docker-compose down` 停止舊容器
- [ ] 執行 `docker-compose up -d --build` 啟動新容器
- [ ] 瀏覽器訪問 `http://localhost:8001` 可以看到測試頁面
- [ ] 測試頁面顯示系統健康狀態為 "健康"
- [ ] Maximo 連接測試成功

## 常見問題

### Q1: Maximo 連接失敗 (unhealthy)

**可能原因：**
1. `MAXIMO_API_KEY` 未配置或無效
2. `MAXIMO_API_URL` 不正確
3. 網絡無法連接到 Maximo 服務器
4. Maximo 服務器未運行

**解決方法：**
1. 檢查 `.env` 文件中的 `MAXIMO_API_KEY` 是否正確
2. 確認 Maximo URL: `http://trs.webdw.xyz:9088/maximo`
3. 測試網絡連接：`curl http://trs.webdw.xyz:9088/maximo/oslc/whoami`
4. 查看容器日誌：`docker-compose logs mcp-server`

### Q2: 系統健康檢查顯示 "degraded"

**原因：** Cache 或 Maximo 其中一個服務不健康

**解決方法：**
- 如果 Cache unhealthy：檢查 Redis 容器是否正常運行 `docker-compose ps`
- 如果 Maximo unhealthy：參考 Q1 的解決方法

### Q3: 測試頁面無法訪問

**解決方法：**
1. 確認容器正在運行：`docker-compose ps`
2. 檢查端口映射：應該是 `8001:8000`
3. 檢查防火牆設置
4. 查看容器日誌：`docker-compose logs mcp-server`

### Q4: 看不到請求/回應日誌

**解決方法：**
1. 刷新瀏覽器頁面 (Ctrl+F5 強制刷新)
2. 日誌區域在頁面最下方，需要向下滾動
3. 開啟瀏覽器開發者工具 (F12) 檢查 JavaScript 錯誤

## 環境變量說明

| 變量名 | 說明 | 必填 | 默認值 |
|--------|------|------|--------|
| `MCP_API_KEY` | Dify 連接 MCP 的認證密鑰 | ✅ | - |
| `MAXIMO_API_KEY` | Maximo API 認證密鑰 | ✅ | - |
| `MAXIMO_API_URL` | Maximo 實例 URL | ✅ | - |
| `PORT` | 外部訪問端口 | ❌ | 8001 |
| `REDIS_HOST` | Redis 主機 | ❌ | redis |
| `LOG_LEVEL` | 日誌級別 | ❌ | INFO |
| `CACHE_TTL_ASSET` | 資產緩存時間(秒) | ❌ | 600 |

## 下一步

配置完成後，您可以：

1. **測試 MCP Tools**：在測試頁面輸入測試數據，驗證各個 API 功能
2. **連接 Dify**：使用 MCP Server URL 和 API Key 在 Dify 中配置 MCP 連接
3. **查看日誌**：`docker-compose logs -f mcp-server` 監控服務運行狀態

## 技術支持

如遇到問題，請提供：
1. `.env` 文件內容（隱藏 API Keys）
2. 容器日誌：`docker-compose logs mcp-server`
3. 錯誤截圖
4. 測試頁面的請求/回應日誌
