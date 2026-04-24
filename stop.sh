#!/usr/bin/env bash
# RAN Omniverse Platform 停止腳本 (詳細步驟版)

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 工具函數
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
    echo -e "${BLUE}   ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}   ✓ $1${NC}"
}

log_error() {
    echo -e "${RED}   ✗ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}   ⚠ $1${NC}"
}

log_code() {
    echo -e "${YELLOW}   $ $1${NC}"
}

pause_step() {
    echo ""
    echo -e "${CYAN}[按 Enter 繼續]${NC}"
    read -r
}

# ============================================================================
# 步驟 1：停止 Kit
# ============================================================================

step_stop_kit() {
    log_header "步驟 1️⃣  停止 Kit 程序"

    log_step "檢查 Kit 狀態..."

    if [ -f "${HERE}/.kit.pid" ]; then
        KIT_PID=$(cat "${HERE}/.kit.pid")

        if kill -0 "$KIT_PID" 2>/dev/null; then
            log_info "Kit 正在運行"
            log_info "PID: $KIT_PID"
            log_info "將發送 SIGTERM 信號..."
            log_code "kill $KIT_PID"

            kill "$KIT_PID"
            sleep 2

            if kill -0 "$KIT_PID" 2>/dev/null; then
                log_warn "Kit 仍在運行，發送 SIGKILL..."
                kill -9 "$KIT_PID"
                sleep 1
            fi

            log_success "Kit 已停止"
            rm -f "${HERE}/.kit.pid"
        else
            log_warn "PID $KIT_PID 的程序不存在"
            rm -f "${HERE}/.kit.pid"
        fi
    else
        log_step "嘗試通用停止方法..."

        if pgrep -f "omni.kit_app" >/dev/null; then
            log_info "找到 Kit 程序，正在停止..."
            log_code "pkill -f 'omni.kit_app'"
            pkill -f "omni.kit_app" || true
            sleep 2
            log_success "Kit 已停止"
        else
            log_info "Kit 不在運行"
        fi
    fi

    pause_step
}

# ============================================================================
# 步驟 2：停止 Docker
# ============================================================================

step_stop_docker() {
    log_header "步驟 2️⃣  停止 Docker 容器"

    log_step "檢查 Docker 容器狀態..."

    if ! command -v docker &>/dev/null; then
        log_error "Docker 命令不可用"
        pause_step
        return 1
    fi

    cd "${HERE}"

    if docker compose ps 2>/dev/null | grep -q "omniver_"; then
        log_info "發現 3 個運行中的容器："
        docker compose ps | grep omniver_

        echo ""
        log_info "停止選項："
        log_info "  1️⃣  保留數據庫（推薦）：docker compose down"
        log_info "  2️⃣  刪除數據庫數據：docker compose down -v"

        pause_step

        log_step "執行 docker compose down..."
        log_code "cd ${HERE} && docker compose down"

        if docker compose down; then
            log_success "Docker 容器已停止"
        else
            log_error "Docker 停止失敗"
            return 1
        fi

        sleep 2

        log_step "驗證容器狀態..."
        if docker compose ps 2>/dev/null | grep -q "omniver_"; then
            log_error "仍有容器在運行"
        else
            log_success "所有容器已停止"
        fi
    else
        log_info "沒有運行中的 Docker 容器"
    fi

    pause_step
}

# ============================================================================
# 步驟 3：清理和驗證
# ============================================================================

step_cleanup() {
    log_header "步驟 3️⃣  清理和驗證"

    log_step "清理臨時文件..."

    if [ -f "${HERE}/.kit.pid" ]; then
        rm -f "${HERE}/.kit.pid"
        log_success "Kit PID 文件已刪除"
    fi

    log_step "驗證所有服務已停止..."

    echo ""
    echo -n "  Kit 程序：    "
    if pgrep -f "omni.kit_app" >/dev/null 2>&1; then
        echo -e "${RED}✗ 仍在運行${NC}"
    else
        echo -e "${GREEN}✓ 已停止${NC}"
    fi

    echo -n "  Docker 容器：  "
    if docker compose ps 2>/dev/null | grep -q "omniver_"; then
        echo -e "${RED}✗ 仍在運行${NC}"
    else
        echo -e "${GREEN}✓ 已停止${NC}"
    fi

    echo -n "  HTTP :8080：  "
    if nc -z localhost 8080 2>/dev/null; then
        echo -e "${RED}✗ 仍監聽${NC}"
    else
        echo -e "${GREEN}✓ 已釋放${NC}"
    fi

    echo -n "  HTTP :8001：  "
    if nc -z localhost 8001 2>/dev/null; then
        echo -e "${RED}✗ 仍監聽${NC}"
    else
        echo -e "${GREEN}✓ 已釋放${NC}"
    fi

    echo -n "  HTTP :3001：  "
    if nc -z localhost 3001 2>/dev/null; then
        echo -e "${RED}✗ 仍監聽${NC}"
    else
        echo -e "${GREEN}✓ 已釋放${NC}"
    fi

    pause_step
}

# ============================================================================
# 步驟 4：顯示摘要
# ============================================================================

step_summary() {
    log_header "步驟 4️⃣  停止完成"

    log_success "所有服務已停止"

    echo ""
    log_info "📊 當前狀態："
    log_code "docker compose ps"
    log_code "pgrep -f 'omni.kit_app' || echo '無運行的 Kit 程序'"

    echo ""
    log_info "🗄️  數據庫："
    log_info "  ✓ Postgres 數據已保留"
    log_info "  若要完全清除數據："
    log_code "docker compose down -v"

    echo ""
    log_info "🔄 重新啟動："
    log_code "${HERE}/start.sh"

    echo ""
    log_info "📖 查看日誌："
    log_code "cat ${HERE}/startup.log"
    log_code "cat ${HERE}/kit.log"

    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              系統已完全停止 👋                        ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ============================================================================
# 主程序
# ============================================================================

main() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔════════════════════════════════════════════════════════╗
║                                                        ║
║   🛑 RAN Omniverse Platform 停止程序                  ║
║                                                        ║
║   這個腳本將一步步停止所有服務：                      ║
║   • 停止 Kit (3D 渲染引擎)                            ║
║   • 停止 Docker (所有容器)                            ║
║   • 驗證所有服務已停止                                ║
║                                                        ║
║   數據庫數據將被保留（可選刪除）                      ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    pause_step

    step_stop_kit
    step_stop_docker
    step_cleanup
    step_summary
}

# ============================================================================
# 執行
# ============================================================================

main "$@"
