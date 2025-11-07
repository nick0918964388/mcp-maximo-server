# 用戶管理功能測試指南

本文檔說明如何測試新增的用戶帳號解鎖與狀態查詢功能。

## Maximo 物件資訊

- **物件結構**: DMMAXUSER
- **資料表**: MAXUSER
- **API 端點**: `/oslc/os/dmmaxuser`

## 新增的 MCP Tools

### 1. get_user_status
查詢用戶帳號狀態和詳細資訊

**參數：**
- `userid` (必填): 用戶 ID (登入帳號)

**回傳資訊：**
- `userid`: 用戶 ID
- `personid`: 人員 ID
- `displayname`: 顯示名稱
- `status`: 用戶狀態 (ACTIVE/INACTIVE)
- `loginid`: 登入 ID
- `lockedout`: 帳號鎖定狀態 (true/false)
- `failedlogincount`: 登入失敗次數
- `emailaddress`: 電子郵件
- `primaryphone`: 主要電話
- `is_locked`: 是否被鎖定 (便於判讀)
- `is_active`: 是否啟用 (便於判讀)
- `failed_login_count`: 失敗登入次數 (便於判讀)

---

### 2. search_users
搜尋用戶

**參數：**
- `query` (可選): 搜尋關鍵字 (搜尋 userid, displayname, personid)
- `status` (可選): 用戶狀態篩選 (如 ACTIVE, INACTIVE)
- `personid` (可選): 人員 ID 篩選
- `locked_only` (可選): 是否只顯示被鎖定的帳號 (預設: false)
- `page_size` (可選): 最大回傳筆數 (預設: 100)

**回傳：**
- 符合條件的用戶列表

---

### 3. unlock_user_account
解鎖用戶帳號

**參數：**
- `userid` (必填): 要解鎖的用戶 ID
- `memo` (可選): 解鎖操作備註

**功能說明：**
此工具會執行以下操作來解鎖帳號：
1. 設定 `status` 為 "ACTIVE"
2. 設定 `lockedout` 為 0 (false)
3. 重設 `failedlogincount` 為 0

**回傳：**
- 更新後的用戶資訊

---

## 測試方法

### 方法 1: 透過 HTTP API 端點測試

啟動服務後，可使用以下 API 端點測試：

#### 1. 測試查詢用戶狀態

```bash
curl -X POST http://localhost:8000/api/test-tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_user_status",
    "params": {
      "userid": "testuser"
    }
  }'
```

#### 2. 測試搜尋用戶

```bash
# 搜尋所有用戶
curl -X POST http://localhost:8000/api/test-tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "search_users",
    "params": {
      "query": "admin",
      "page_size": 10
    }
  }'

# 只搜尋被鎖定的帳號
curl -X POST http://localhost:8000/api/test-tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "search_users",
    "params": {
      "locked_only": true
    }
  }'
```

#### 3. 測試解鎖帳號

```bash
curl -X POST http://localhost:8000/api/test-tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "unlock_user_account",
    "params": {
      "userid": "testuser",
      "memo": "手動解鎖帳號"
    }
  }'
```

---

### 方法 2: 透過 MCP Protocol (由 Dify 調用)

在 Dify Agent 中配置 MCP 連接後，可直接使用這些工具：

#### 範例對話 1: 查詢用戶狀態
```
用戶: 請查詢 testuser 的帳號狀態
Agent: [調用 get_user_status 工具]
```

#### 範例對話 2: 搜尋被鎖定的帳號
```
用戶: 列出所有被鎖定的用戶帳號
Agent: [調用 search_users 工具，設定 locked_only=true]
```

#### 範例對話 3: 解鎖帳號
```
用戶: 請解鎖 testuser 的帳號
Agent: [調用 unlock_user_account 工具]
```

---

### 方法 3: 透過互動式測試頁面

1. 啟動服務後，開啟瀏覽器訪問 `http://localhost:8000/test`
2. 在測試頁面中選擇相應的工具進行測試
3. 注意：需要更新 `static/test.html` 以包含新的用戶管理工具

---

## 環境設定

確保 `.env` 檔案中已設定以下環境變數：

```env
# Maximo API Configuration
MAXIMO_API_URL=https://your-maximo-server.com
MAXIMO_API_KEY=your-api-key
MAXIMO_MAXAUTH=your-maxauth-token

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Server Configuration
PORT=8000
CORS_ENABLED=true
```

---

## 啟動服務

### 使用 Docker Compose (推薦)
```bash
docker-compose up -d
```

### 本地運行
```bash
# 安裝依賴
pip install -r requirements.txt

# 啟動 Redis (需要另外安裝)
redis-server

# 啟動 MCP Server
python -m src.main
```

---

## 快取機制

用戶查詢結果會被快取，預設 TTL 為 600 秒 (10 分鐘)。
當執行解鎖操作時，相關的快取會自動失效。

---

## 錯誤處理

所有工具都包含完整的錯誤處理：

1. **用戶不存在**: 回傳 404 錯誤
2. **認證失敗**: 回傳 401 錯誤
3. **網路錯誤**: 自動重試 (最多 3 次)
4. **超時**: 預設超時時間為 30 秒

---

## 日誌記錄

所有操作都會記錄結構化日誌，包括：
- 請求參數
- 執行時間
- 錯誤資訊
- 關鍵操作 (如解鎖帳號)

查看日誌：
```bash
# 如果使用 Docker
docker-compose logs -f mcp-server

# 如果本地運行
# 日誌會輸出到標準輸出
```

---

## 安全注意事項

1. **權限控制**: 確保只有授權的用戶可以調用解鎖功能
2. **審計記錄**: 所有解鎖操作都會記錄在日誌中
3. **API Key 保護**: 不要將 API Key 提交到版本控制系統
4. **HTTPS**: 生產環境應使用 HTTPS 連接 Maximo

---

## 檔案變更清單

本次更新包含以下檔案變更：

1. **新增檔案**:
   - `src/tools/user_tools.py` - 用戶管理工具實作

2. **修改檔案**:
   - `src/main.py` - 註冊新的 MCP tools 和測試端點

3. **文檔**:
   - `USER_MANAGEMENT_TESTING.md` - 本測試指南

---

## 後續改進建議

1. 更新 `static/test.html` 以包含用戶管理工具的測試介面
2. 添加更多用戶管理功能，如：
   - 批次解鎖多個帳號
   - 設定用戶狀態 (啟用/停用)
   - 查看用戶登入歷史
   - 重設密碼
3. 添加單元測試和整合測試
4. 實作更細緻的權限控制

---

## 支援與反饋

如有問題或建議，請聯繫開發團隊。
