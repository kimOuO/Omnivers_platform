#!/usr/bin/env bash
# RAN Omniverse Platform 啟動腳本 (詳細步驟版)
# 每一步都有說明和確認

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="${HERE}/startup.log"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 清除日誌
echo "RAN Omniverse Platform Startup - $(date)" > "$LOG_FILE"

# ============================================================================
# 工具函數
# ============================================================================

log_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║ $1${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
}

log_step() {
    echo -e "${BLUE}📍 $1${NC}"
}

log_info() {
    echo -e "${BLUE}   ℹ️  $1${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}   ✓ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}   ✗ $1${NC}" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}   ⚠ $1${NC}" | tee -a "$LOG_FILE"
}

log_code() {
    echo -e "${YELLOW}   $ $1${NC}"
}

pause_step() {
    echo ""
    echo -e "${CYAN}[按 Enter 繼續 或 Ctrl+C 中止]${NC}"
    read -r
}

# ============================================================================
# 步驟 1：檢查前置條件
# ============================================================================

step_check_prerequisites() {
    log_header "步驟 1️⃣  檢查前置條件"

    log_step "檢查 Python venv..."
    log_info "需要：~/omniverse-env (安裝了 omniverse-kit)"

    if [ -f "${HOME}/omniverse-env/bin/activate" ]; then
        log_success "找到 ~/omniverse-env"
    else
        log_error "找不到 ~/omniverse-env"
        log_info "請先執行："
        log_code "pip install omniverse-kit --extra-index-url https://pypi.nvidia.com"
        echo -e "${RED}無法繼續${NC}"
        exit 1
    fi

    log_step "檢查 Docker..."
    if command -v docker &> /dev/null; then
        log_success "Docker 已安裝"
    else
        log_error "找不到 Docker"
        log_info "請先安裝 Docker：https://docs.docker.com/get-docker/"
        exit 1
    fi

    log_step "檢查 scene_config.json..."
    if [ -f "${HERE}/scene_config.json" ]; then
        log_success "scene_config.json 存在於 ${HERE}"
    else
        log_warn "scene_config.json 不存在"
        log_info "可使用環境變數 RAN_SCENE_CONFIG 指定其他位置"
    fi

    log_step "檢查 DISPLAY..."
    if [ -n "${DISPLAY:-}" ]; then
        log_success "DISPLAY = $DISPLAY"
    else
        log_warn "DISPLAY 未設定"
        log_info "需要本地 X11 或 VNC："
        log_info "  本地：export DISPLAY=:0"
        log_info "  VNC：export DISPLAY=:88"
    fi

    log_step "檢查 extscache..."
    if [ -d "/home/mitlab/Omniverse/kit-app-template/_build/linux-x86_64/release/extscache" ]; then
        log_success "extscache 存在"
    else
        log_warn "extscache 不存在（Kit 可能無法啟動）"
        log_info "請先執行：cd kit-app-template && ./repo.sh build"
    fi

    log_success "前置條件檢查完成"
    pause_step
}

# ============================================================================
# 步驟 2：啟動 Docker
# ============================================================================

step_start_docker() {
    log_header "步驟 2️⃣  啟動 Docker 容器"

    log_step "檢查 Docker 容器狀態..."
    if docker compose -f "${HERE}/docker-compose.yml" ps 2>/dev/null | grep -q "omniver_postgres"; then
        log_warn "Docker 容器已在運行，跳過啟動"
        pause_step
        return 0
    fi

    log_info "將啟動 3 個容器："
    log_info "  1. omniver_postgres (port 5432) - 數據庫"
    log_info "  2. omniver_backend  (port 8001) - Django API"
    log_info "  3. omniver_frontend (port 3001) - Next.js 前端"
    log_info ""
    log_info "首次啟動會 build backend image (3-5 分鐘)"

    pause_step

    log_step "執行 docker compose up -d..."
    log_code "cd ${HERE} && docker compose up -d"

    cd "${HERE}"
    if docker compose up -d; then
        log_success "Docker 容器啟動成功"
    else
        log_error "Docker 啟動失敗"
        exit 1
    fi

    sleep 3

    log_step "驗證容器狀態..."
    docker compose ps
    log_success "所有容器已啟動"

    pause_step
}

# ============================================================================
# 步驟 3：啟動 Kit
# ============================================================================

step_start_kit() {
    log_header "步驟 3️⃣  啟動 Omniverse Kit"

    log_info "Kit 是 RAN Digital Twin 的 3D 核心"
    log_info "  - 需要 GPU 和顯示器（X11 或 VNC）"
    log_info "  - 首次啟動可能需要接受 EULA"
    log_info "  - 將在背景執行，持續監聽 port 8080"
    log_info ""
    log_info "檢查項目："

    if [ -z "${VIRTUAL_ENV:-}" ]; then
        if [ -f "${HOME}/omniverse-env/bin/activate" ]; then
            log_info "  - 激活 Python venv..."
            source "${HOME}/omniverse-env/bin/activate"
            log_success "venv 已激活"
        fi
    fi

    if [ -z "${DISPLAY:-}" ]; then
        log_warn "  - DISPLAY 未設定！Kit 可能無法顯示"
        log_info "請在另一個終端設定："
        log_info "  export DISPLAY=:0 (本地)"
        log_info "  export DISPLAY=:88 (VNC)"
    else
        log_success "  - DISPLAY = $DISPLAY"
    fi

    pause_step

    log_step "執行 ./kit/run.sh..."
    log_code "cd ${HERE}/kit && ./run.sh"
    log_info "（在背景執行，日誌寫入 ${HERE}/kit.log）"

    cd "${HERE}/kit"
    ./run.sh > "${HERE}/kit.log" 2>&1 &
    KIT_PID=$!
    echo $KIT_PID > "${HERE}/.kit.pid"

    log_success "Kit 已在背景啟動"
    log_info "PID: $KIT_PID"
    log_info "日誌位置：${HERE}/kit.log"
    log_info "查看日誌：tail -f ${HERE}/kit.log"

    pause_step
}

# ============================================================================
# 步驟 4：等待服務就緒
# ============================================================================

step_wait_services() {
    log_header "步驟 4️⃣  等待服務初始化"

    log_info "Kit 初始化需要時間（包括 Vulkan 初始化）"
    log_info "預計：10-20 秒"
    log_info ""
    log_info "正在等待..."

    sleep 3

    local services=(
        "8001:Django"
        "3001:Next.js"
        "5432:Postgres"
    )

    for service_info in "${services[@]}"; do
        port="${service_info%%:*}"
        name="${service_info##*:}"

        echo -n "  ⏳ $name (port $port)..."
        local attempt=0
        while [ $attempt -lt 30 ]; do
            if nc -z localhost "$port" 2>/dev/null; then
                echo -e " ${GREEN}✓${NC}"
                log_success "$name 就緒"
                break
            fi
            echo -n "."
            sleep 1
            attempt=$((attempt + 1))
        done

        if [ $attempt -eq 30 ]; then
            echo -e " ${YELLOW}⏱${NC}"
            log_warn "$name 超時（可能需要更多時間）"
        fi
    done

    echo -n "  ⏳ Kit HTTP (port 8080)..."
    local attempt=0
    while [ $attempt -lt 40 ]; do
        if nc -z localhost 8080 2>/dev/null; then
            echo -e " ${GREEN}✓${NC}"
            log_success "Kit HTTP API 就緒"
            break
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done

    if [ $attempt -eq 40 ]; then
        echo -e " ${YELLOW}⏱${NC}"
        log_warn "Kit HTTP API 尚未就緒（初始化中...）"
        log_info "Kit 可能正在初始化渲染器，請耐心等待"
    fi

    pause_step
}

# ============================================================================
# 步驟 5：驗證服務
# ============================================================================

step_verify() {
    log_header "步驟 5️⃣  驗證所有服務"

    log_step "檢查 Postgres..."
    if docker exec omniver_postgres pg_isready -U ran -d ran_dt &>/dev/null; then
        log_success "Postgres 就緒"
    else
        log_warn "Postgres 無法連接"
    fi

    log_step "檢查 Django..."
    if curl -s -X POST http://localhost:8001/api/v0.1/RAN/Scene/SceneStateReader/read \
        -H "Content-Type: application/json" -d '{}' | grep -q "success"; then
        log_success "Django API 正常"
    else
        log_warn "Django API 無響應或異常"
    fi

    log_step "檢查 Next.js..."
    if curl -s http://localhost:3001/ | grep -q "html"; then
        log_success "Next.js 前端就緒"
    else
        log_warn "Next.js 無響應"
    fi

    log_step "檢查 Kit HTTP API..."
    if curl -s http://localhost:8080/ | grep -q "RAN Digital Twin"; then
        log_success "Kit HTTP API 正常"
    else
        log_warn "Kit HTTP API 尚未就緒（可能還在初始化）"
    fi

    pause_step
}

# ============================================================================
# 步驟 6：顯示完整狀態
# ============================================================================

step_summary() {
    log_header "步驟 6️⃣  啟動完成！"

    log_success "所有服務已啟動"
    echo ""

    log_info "🌐 服務地址："
    echo -e "   ${CYAN}• Next.js 前端：${NC}     http://localhost:3001"
    echo -e "   ${CYAN}• Django 後端：${NC}      http://localhost:8001"
    echo -e "   ${CYAN}• Kit HTTP API：${NC}     http://localhost:8080"
    echo -e "   ${CYAN}• Postgres DB：${NC}      localhost:5432"
    echo -e "   ${CYAN}• VNC 3D 視圖：${NC}      localhost:5901"

    echo ""
    log_info "📊 查看狀態："
    echo "   $ docker compose ps"
    echo "   $ curl http://localhost:8080/scene/status"
    echo "   $ tail -f ${HERE}/kit.log"

    echo ""
    log_info "🎮 下一步："
    echo "   1️⃣  打開 VNC 或本地 X 視窗"
    echo "   2️⃣  看到 Kit 視窗，點擊『Build Scene』"
    echo "   3️⃣  打開 http://localhost:3001 控制平台"

    echo ""
    log_info "🛑 中止方法："
    echo "   • 停止一切：${HERE}/stop.sh"
    echo "   • 只停止 Docker：docker compose down"
    echo "   • 只停止 Kit：kill \$(cat ${HERE}/.kit.pid)"
    echo "   • Ctrl+C 中止此腳本（已在背景執行，無影響）"

    echo ""
    log_info "📖 更多資訊："
    echo "   $ cat ${HERE}/QUICKSTART.md"
    echo "   $ cat ${HERE}/extensions/README.md"

    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              祝你使用愉快！🚀                          ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ============================================================================
# 主程序
# ============================================================================

main() {
    trap 'log_error "啟動被中止"; exit 130' INT TERM

    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔════════════════════════════════════════════════════════╗
║                                                        ║
║   🚀 RAN Omniverse Platform 啟動程序                  ║
║                                                        ║
║   這個腳本將一步步引導您啟動完整系統                  ║
║   • 檢查前置條件                                      ║
║   • 啟動 Docker (3 個容器)                            ║
║   • 啟動 Kit (3D 渲染引擎)                            ║
║   • 驗證所有服務                                      ║
║                                                        ║
║   每一步都有詳細說明，按 Enter 繼續                    ║
║   按 Ctrl+C 隨時中止                                  ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    pause_step

    step_check_prerequisites
    step_start_docker
    step_start_kit
    step_wait_services
    step_verify
    step_summary
}

# ============================================================================
# 執行
# ============================================================================

main "$@"
