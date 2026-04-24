# 🚀 快速啟動指南

只需三個命令，5 分鐘內啟動完整系統。

---

## 最簡單的方式：菜單

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform
./run.sh
```

選擇菜單中的 **1️⃣ 完整啟動**，所有事都自動做好。

---

## 或者：直接執行腳本

### 快速啟動

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform
./start.sh
```

這會：
1. ✅ 檢查前置條件
2. ✅ 啟動 Docker (Postgres + Django + Next.js)
3. ✅ 啟動 Kit
4. ✅ 驗證所有服務
5. ✅ 顯示完整狀態

等待 ~10-15 秒。

### 停止所有服務

```bash
./stop.sh
```

---

## 服務地址

啟動完成後，訪問：

```
🌐 Next.js 前端：      http://localhost:3001
⚙️  Django 後端：      http://localhost:8001
📡 Kit HTTP API：      http://localhost:8080
🎮 VNC 3D 視圖：       localhost:5901 (自動開啟)
```

---

## 驗證啟動成功

```bash
# 方式 1：查看 Kit 日誌
tail -f startup.log

# 方式 2：測試 API
curl http://localhost:8080/
curl http://localhost:8080/scene/status

# 方式 3：查看 Docker
docker compose ps

# 方式 4：打開瀏覽器
open http://localhost:3001
```

---

## 常見命令

| 操作 | 命令 |
|------|------|
| 完整啟動 | `./start.sh` |
| 停止所有 | `./stop.sh` |
| 菜單 | `./run.sh` |
| 查看 Kit 日誌 | `tail -f kit.log` |
| 查看啟動日誌 | `tail -f startup.log` |
| Docker 狀態 | `docker compose ps` |
| 刪除數據庫 | `docker compose down -v` |

---

## 下一步

1. **打開前端**  
   http://localhost:3001

2. **建構場景**  
   在 VNC 點擊「Build Scene」或執行：
   ```bash
   curl -X POST http://localhost:8080/scene/build
   ```

3. **移動 UE**  
   ```bash
   curl -X POST http://localhost:8080/ue/UE_1/move \
     -H "Content-Type: application/json" \
     -d '{"x": 100, "y": 50, "z": 200}'
   ```

4. **查看詳細文檔**  
   ```bash
   cat extensions/README.md
   ```

---

## 故障排排

### Kit 秒退

```
症狀：./start.sh 後馬上結束
原因：DISPLAY 未設定或 GPU 驅動問題

解決：
# 檢查 DISPLAY
echo $DISPLAY
# 應該是 :0 (本地) 或 :88 (VNC)

# 若無，設定：
export DISPLAY=:0    # 本地
export DISPLAY=:88   # VNC
```

### Docker 啟動失敗

```
症狀：omniver_postgres 無法啟動
原因：port 已被佔用或 Docker daemon 未啟動

解決：
# 檢查 Docker
docker ps

# 若無法連接，啟動 Docker daemon
sudo systemctl start docker

# 刪除舊容器
docker compose down -v
docker compose up -d
```

### Kit 卡在 EULA

```
症狀：./start.sh 卡住不動
原因：首次執行需要接受 EULA

解決：
# 查看 Kit 日誌
tail -f kit.log
# 應該看到 "Do you accept the EULA? (Yes/No):"
# 在那個終端輸入 "Yes" 並按 Enter
```

### Django 連接不到 Kit

```
症狀：Django 日誌狂噴 ConnectionRefusedError :8080
原因：Kit 還沒啟動或 HTTP :8080 還沒就緒

解決：
# 這是正常的！Django 會自動重試
# 等待 Kit 完全啟動（10-15 秒）
tail -f kit.log | grep "HTTP :8080"
```

---

## 📚 更多資訊

- **詳細啟動流程**：`cat extensions/README.md`
- **架構設計**：`cat extensions/README.md | grep -A 50 "四層架構"`
- **HTTP API**：`curl http://localhost:8080/`
- **線程模型**：`cat extensions/README.md | grep -A 30 "線程模型"`

---

## 快速鍵

```bash
# 一鍵完整啟動
cd /home/mitlab/XAPP_DT/Omnivers_platform && ./start.sh

# 一鍵停止
cd /home/mitlab/XAPP_DT/Omnivers_platform && ./stop.sh

# 查看所有服務狀態
docker compose ps && curl http://localhost:8080/scene/status

# 測試完整流程
curl -X POST http://localhost:8080/scene/build && \
  sleep 5 && \
  curl http://localhost:8080/scene/status
```

---

**現在就試試吧！** 🚀

```bash
./start.sh
```
