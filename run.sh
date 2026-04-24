#!/usr/bin/env bash
# RAN Omniverse Platform 互動菜單

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

clear_screen() {
    clear
}

# ============================================================================
# 菜單顯示
# ============================================================================

show_header() {
    clear_screen
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🚀 RAN Omniverse Platform - 控制菜單                   ║
║                                                           ║
║   選擇操作或按 Ctrl+C 退出                              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

show_menu() {
    echo ""
    echo -e "${GREEN}╔ 核心操作 ════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${MAGENTA}1️⃣${NC}  ${YELLOW}啟動完整系統${NC}  (Docker + Kit + 驗證)"
    echo -e "${GREEN}║${NC}        一鍵啟動，所有操作自動化"
    echo -e "${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${MAGENTA}2️⃣${NC}  ${YELLOW}停止所有服務${NC}  (Kit + Docker)"
    echo -e "${GREEN}║${NC}        保留數據庫，可隨時重啟"
    echo -e "${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"

    echo ""
    echo -e "${BLUE}╔ 單獨操作 ════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${MAGENTA}3️⃣${NC}  只啟動 Docker (Postgres + Django + Next.js)"
    echo -e "${BLUE}║${NC}  ${MAGENTA}4️⃣${NC}  只停止 Docker"
    echo -e "${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${MAGENTA}5️⃣${NC}  只啟動 Kit (3D 渲染引擎)"
    echo -e "${BLUE}║${NC}  ${MAGENTA}6️⃣${NC}  只停止 Kit"
    echo -e "${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"

    echo ""
    echo -e "${YELLOW}╔ 查看狀態 & 日誌 ═════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  ${MAGENTA}7️⃣${NC}  查看系統狀態   (各個服務是否運行)"
    echo -e "${YELLOW}║${NC}  ${MAGENTA}8️⃣${NC}  查看 Kit 日誌    (實時檢查 Kit 初始化進度)"
    echo -e "${YELLOW}║${NC}  ${MAGENTA}9️⃣${NC}  查看啟動日誌    (完整的啟動過程記錄)"
    echo -e "${YELLOW}║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════╝${NC}"

    echo ""
    echo -e "${CYAN}╔ 測試 & 驗證 ═════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${MAGENTA}🔟${NC}  驗證所有服務   (檢查是否就緒)"
    echo -e "${CYAN}║${NC}  ${MAGENTA}⓪${NC}  測試 HTTP API  (curl 測試 Kit)"
    echo -e "${CYAN}║${NC}  ${MAGENTA}@${NC}  測試 Django    (curl 測試後端)"
    echo -e "${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"

    echo ""
    echo -e "${MAGENTA}╔ 文檔 & 其他 ═════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}  ${MAGENTA}d${NC}  查看快速開始     (QUICKSTART.md)"
    echo -e "${MAGENTA}║${NC}  ${MAGENTA}r${NC}  查看完整文檔     (extensions/README.md)"
    echo -e "${MAGENTA}║${NC}  ${MAGENTA}h${NC}  顯示幫助         (使用說明)"
    echo -e "${MAGENTA}║${NC}  ${MAGENTA}q${NC}  退出菜單"
    echo -e "${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════╝${NC}"

    echo ""
}

# ============================================================================
# 操作函數
# ============================================================================

do_full_start() {
    echo ""
    echo -e "${YELLOW}正在啟動完整系統...${NC}"
    echo -e "${BLUE}(按 Ctrl+C 隨時中止)${NC}"
    echo ""
    "${HERE}/start.sh"
}

do_full_stop() {
    echo ""
    echo -e "${YELLOW}正在停止所有服務...${NC}"
    echo -e "${BLUE}(按 Ctrl+C 隨時中止)${NC}"
    echo ""
    "${HERE}/stop.sh"
}

do_start_docker() {
    echo ""
    echo -e "${YELLOW}只啟動 Docker 容器...${NC}"
    cd "${HERE}"
    docker compose up -d
    sleep 2
    echo ""
    echo -e "${GREEN}✓ Docker 容器已啟動${NC}"
    docker compose ps
    echo ""
    echo -e "${BLUE}按 Enter 返回菜單...${NC}"
    read -r
}

do_stop_docker() {
    echo ""
    echo -e "${YELLOW}停止 Docker 容器...${NC}"
    cd "${HERE}"
    docker compose down
    sleep 1
    echo -e "${GREEN}✓ Docker 容器已停止${NC}"
    echo ""
    echo -e "${BLUE}提示：數據庫數據已保留${NC}"
    echo -e "${BLUE}若要刪除所有數據：docker compose down -v${NC}"
    echo ""
    echo -e "${BLUE}按 Enter 返回菜單...${NC}"
    read -r
}

do_start_kit() {
    echo ""
    echo -e "${YELLOW}啟動 Kit 程序...${NC}"
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        if [ -f "${HOME}/omniverse-env/bin/activate" ]; then
            source "${HOME}/omniverse-env/bin/activate"
        fi
    fi
    cd "${HERE}/kit"
    ./run.sh > "${HERE}/kit.log" 2>&1 &
    KIT_PID=$!
    echo $KIT_PID > "${HERE}/.kit.pid"
    echo ""
    echo -e "${GREEN}✓ Kit 已在背景啟動${NC}"
    echo -e "  PID: $KIT_PID"
    echo -e "  日誌: ${HERE}/kit.log"
    echo ""
    echo -e "${BLUE}按 Enter 返回菜單...${NC}"
    read -r
}

do_stop_kit() {
    echo ""
    if [ -f "${HERE}/.kit.pid" ]; then
        KIT_PID=$(cat "${HERE}/.kit.pid")
        if kill -0 "$KIT_PID" 2>/dev/null; then
            echo -e "${YELLOW}停止 Kit (PID: $KIT_PID)...${NC}"
            kill "$KIT_PID" 2>/dev/null || true
            sleep 2
            if kill -0 "$KIT_PID" 2>/dev/null; then
                kill -9 "$KIT_PID" 2>/dev/null || true
            fi
            rm -f "${HERE}/.kit.pid"
            echo -e "${GREEN}✓ Kit 已停止${NC}"
        else
            echo -e "${YELLOW}⚠ Kit 程序不存在${NC}"
        fi
    else
        pkill -f "omni.kit_app" || true
        echo -e "${GREEN}✓ Kit 已停止${NC}"
    fi
    echo ""
    echo -e "${BLUE}按 Enter 返回菜單...${NC}"
    read -r
}

do_view_status() {
    clear_screen
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                      系統狀態                             ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    echo -e "${BLUE}📦 Docker 容器：${NC}"
    docker compose -f "${HERE}/docker-compose.yml" ps 2>/dev/null || echo "Docker 未啟動"
    echo ""

    echo -e "${BLUE}🎮 Kit 程序：${NC}"
    if [ -f "${HERE}/.kit.pid" ]; then
        KIT_PID=$(cat "${HERE}/.kit.pid")
        if kill -0 "$KIT_PID" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Kit 正在運行 (PID: $KIT_PID)"
        else
            echo -e "  ${RED}✗${NC} Kit 未運行"
        fi
    else
        if pgrep -f "omni.kit_app" >/dev/null; then
            echo -e "  ${GREEN}✓${NC} Kit 正在運行 (PID 未知)"
        else
            echo -e "  ${RED}✗${NC} Kit 未運行"
        fi
    fi
    echo ""

    echo -e "${BLUE}🌐 網路服務：${NC}"
    for port in 3001 8001 8080 5432; do
        service=""
        case $port in
            3001) service="Next.js 前端" ;;
            8001) service="Django 後端" ;;
            8080) service="Kit HTTP API" ;;
            5432) service="Postgres DB" ;;
        esac
        echo -n "  $service (port $port)："
        if nc -z localhost "$port" 2>/dev/null; then
            echo -e " ${GREEN}✓ 就緒${NC}"
        else
            echo -e " ${RED}✗ 不可達${NC}"
        fi
    done
    echo ""

    echo -e "${BLUE}按 Enter 返回菜單...${NC}"
    read -r
}

do_view_kit_log() {
    if [ ! -f "${HERE}/kit.log" ]; then
        echo -e "${RED}✗ 找不到 Kit 日誌${NC}"
        echo "  請先啟動 Kit"
        echo ""
        echo -e "${BLUE}按 Enter 返回菜單...${NC}"
        read -r
        return
    fi

    clear_screen
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                    Kit 日誌 (實時)                        ║
║          (按 Ctrl+C 停止跟蹤，返回菜單)                   ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    tail -f "${HERE}/kit.log" 2>/dev/null || {
        echo -e "${RED}✗ 無法讀取日誌${NC}"
        read -r
    }
}

do_view_startup_log() {
    if [ ! -f "${HERE}/startup.log" ]; then
        echo -e "${RED}✗ 找不到啟動日誌${NC}"
        echo "  請先執行啟動腳本"
        echo ""
        echo -e "${BLUE}按 Enter 返回菜單...${NC}"
        read -r
        return
    fi

    clear_screen
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                  啟動日誌 (最後 50 行)                    ║
║          (按空格查看更多，q 返回菜單)                     ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    tail -50 "${HERE}/startup.log" | less
}

do_verify() {
    echo ""
    echo -e "${YELLOW}驗證所有服務...${NC}"
    echo ""

    local failed=0

    echo -n "Postgres DB：   "
    if docker exec omniver_postgres pg_isready -U ran -d ran_dt &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        failed=$((failed + 1))
    fi

    echo -n "Django 後端：   "
    if curl -s -X POST http://localhost:8001/api/v0.1/RAN/Scene/SceneStateReader/read \
        -H "Content-Type: application/json" -d '{}' | grep -q "success"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        failed=$((failed + 1))
    fi

    echo -n "Next.js 前端：  "
    if curl -s http://localhost:3001/ >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        failed=$((failed + 1))
    fi

    echo -n "Kit HTTP API：  "
    if curl -s http://localhost:8080/ >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        failed=$((failed + 1))
    fi

    echo ""
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}✓ 所有服務就緒！${NC}"
    else
        echo -e "${YELLOW}⚠ $failed 個服務未就緒${NC}"
    fi

    echo ""
    echo -e "${BLUE}按 Enter 返回菜單...${NC}"
    read -r
}

do_test_api() {
    echo ""
    echo -e "${YELLOW}測試 Kit HTTP API...${NC}"
    echo ""
    echo -e "${CYAN}GET http://localhost:8080/${NC}"
    curl -s http://localhost:8080/ | python3 -m json.tool 2>/dev/null || echo "無法連接"
    echo ""
    echo -e "${BLUE}按 Enter 返回菜單...${NC}"
    read -r
}

do_test_django() {
    echo ""
    echo -e "${YELLOW}測試 Django 後端...${NC}"
    echo ""
    echo -e "${CYAN}POST http://localhost:8001/api/v0.1/RAN/Scene/SceneStateReader/read${NC}"
    curl -s -X POST http://localhost:8001/api/v0.1/RAN/Scene/SceneStateReader/read \
        -H "Content-Type: application/json" -d '{}' | python3 -m json.tool 2>/dev/null || echo "無法連接"
    echo ""
    echo -e "${BLUE}按 Enter 返回菜單...${NC}"
    read -r
}

do_view_quickstart() {
    if [ ! -f "${HERE}/QUICKSTART.md" ]; then
        echo -e "${RED}✗ 找不到 QUICKSTART.md${NC}"
        return
    fi
    less "${HERE}/QUICKSTART.md"
}

do_view_readme() {
    if [ ! -f "${HERE}/extensions/README.md" ]; then
        echo -e "${RED}✗ 找不到 extensions/README.md${NC}"
        return
    fi
    less "${HERE}/extensions/README.md"
}

show_help() {
    clear_screen
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                      使用說明                             ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    echo -e "${GREEN}快速開始：${NC}"
    echo "  1. 選擇 '1️⃣ 啟動完整系統' - 自動啟動所有服務"
    echo "  2. 等待 10-15 秒完成初始化"
    echo "  3. 打開瀏覽器：http://localhost:3001"
    echo ""

    echo -e "${GREEN}中止方法：${NC}"
    echo "  • 在任何輸入界面按 Ctrl+C 中止"
    echo "  • 或選擇 '2️⃣ 停止所有服務'"
    echo "  • 或選擇 '6️⃣ 只停止 Kit' + '4️⃣ 只停止 Docker'"
    echo ""

    echo -e "${GREEN}查看進度：${NC}"
    echo "  • 選擇 '7️⃣ 查看系統狀態' - 檢查各個服務"
    echo "  • 選擇 '8️⃣ 查看 Kit 日誌' - 實時跟蹤 Kit 初始化"
    echo "  • 選擇 '🔟 驗證所有服務' - 檢查是否就緒"
    echo ""

    echo -e "${GREEN}故障排查：${NC}"
    echo "  • Kit 無法啟動 → 檢查 DISPLAY 和 GPU 驅動"
    echo "  • Docker 無法啟動 → 檢查 Docker daemon"
    echo "  • 服務連接超時 → 檢查防火牆和 port 占用"
    echo ""

    echo -e "${GREEN}服務地址：${NC}"
    echo "  • Next.js 前端：http://localhost:3001"
    echo "  • Django 後端：http://localhost:8001"
    echo "  • Kit HTTP API：http://localhost:8080"
    echo "  • VNC 3D 視圖：localhost:5901"
    echo ""

    echo -e "${BLUE}按 Enter 返回菜單...${NC}"
    read -r
}

# ============================================================================
# 主循環
# ============================================================================

main() {
    trap 'echo ""; echo -e "${YELLOW}已取消${NC}"; exit 0' INT TERM

    while true; do
        show_header
        show_menu

        echo -n "請選擇 [1-9/0/@/d/r/h/q]: "
        read -r choice

        case "$choice" in
            1) do_full_start ;;
            2) do_full_stop ;;
            3) do_start_docker ;;
            4) do_stop_docker ;;
            5) do_start_kit ;;
            6) do_stop_kit ;;
            7) do_view_status ;;
            8) do_view_kit_log ;;
            9) do_view_startup_log ;;
            0|10) do_verify ;;
            @) do_test_django ;;
            d) do_view_quickstart ;;
            r) do_view_readme ;;
            h) show_help ;;
            q)
                echo ""
                echo -e "${GREEN}再見！${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ 無效選擇${NC}"
                sleep 1
                ;;
        esac
    done
}

# ============================================================================
# 執行
# ============================================================================

main "$@"
