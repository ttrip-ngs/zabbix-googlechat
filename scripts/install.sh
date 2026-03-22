#!/usr/bin/env bash
# zabbix-googlechat インストールスクリプト
# Zabbixサーバーへの自動インストールを行う。
#
# 使用方法:
#   sudo bash install.sh                         # リポジトリからインストール
#   sudo bash install.sh --source /path/to/repo  # ローカルパスからインストール
#   sudo bash install.sh --source git+https://github.com/user/zabbix-googlechat.git
#
# 動作:
#   1. Python 3.10以上の確認
#   2. pip install 実行
#   3. AlertScriptsPath を /etc/zabbix/zabbix_server.conf から自動検出
#   4. zabbix_notify.py を alertscripts にコピー + 実行権限付与
#   5. /etc/zabbix-googlechat/ に config.yaml.example を配置
#   6. 動作確認コマンドを表示

set -euo pipefail

# スクリプトのディレクトリ（リポジトリ内の scripts/ を想定）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "${SCRIPT_DIR}")"

# デフォルト設定
INSTALL_SOURCE="${REPO_ROOT}"
ZABBIX_SERVER_CONF="/etc/zabbix/zabbix_server.conf"
CONFIG_DIR="/etc/zabbix-googlechat"
DEFAULT_ALERTSCRIPTS_PATH="/usr/lib/zabbix/alertscripts"

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# 引数解析
while [[ $# -gt 0 ]]; do
    case "$1" in
        --source)
            INSTALL_SOURCE="$2"
            shift 2
            ;;
        --help|-h)
            echo "使用方法: sudo bash install.sh [--source <path_or_url>]"
            echo ""
            echo "オプション:"
            echo "  --source <path_or_url>  インストール元を指定（デフォルト: リポジトリルート）"
            echo "                          例: /path/to/zabbix-googlechat"
            echo "                          例: git+https://github.com/user/zabbix-googlechat.git"
            exit 0
            ;;
        *)
            error "不明なオプション: $1"
            exit 1
            ;;
    esac
done

# ---- 1. Python バージョン確認 ----
info "Python バージョンを確認中..."

PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [[ "$major" -ge 3 && "$minor" -ge 10 ]]; then
            PYTHON_CMD="$cmd"
            info "Python ${version} を使用: $(command -v "$cmd")"
            break
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    error "Python 3.10 以上が見つかりません。インストールしてください。"
    exit 1
fi

# pip が利用可能か確認
if ! "$PYTHON_CMD" -m pip --version &>/dev/null; then
    error "pip が利用できません。pip をインストールしてください。"
    exit 1
fi

# ---- 2. pip install ----
info "zabbix-googlechat をインストール中: ${INSTALL_SOURCE}"

if "$PYTHON_CMD" -m pip install "${INSTALL_SOURCE}" --quiet; then
    info "インストール完了"
else
    error "pip install に失敗しました。"
    exit 1
fi

# インストール確認
if ! "$PYTHON_CMD" -c "import zabbix_googlechat" 2>/dev/null; then
    error "zabbix_googlechat モジュールのインポートに失敗しました。"
    exit 1
fi

# ---- 3. AlertScriptsPath の検出 ----
info "AlertScriptsPath を検出中..."

ALERTSCRIPTS_PATH=""
if [[ -f "${ZABBIX_SERVER_CONF}" ]]; then
    detected=$(grep -E '^\s*AlertScriptsPath\s*=' "${ZABBIX_SERVER_CONF}" | tail -1 | sed 's/.*=\s*//' | tr -d ' ')
    if [[ -n "$detected" ]]; then
        ALERTSCRIPTS_PATH="$detected"
        info "AlertScriptsPath を検出: ${ALERTSCRIPTS_PATH}"
    else
        warning "zabbix_server.conf に AlertScriptsPath が設定されていません。"
    fi
else
    warning "zabbix_server.conf が見つかりません: ${ZABBIX_SERVER_CONF}"
fi

if [[ -z "$ALERTSCRIPTS_PATH" ]]; then
    ALERTSCRIPTS_PATH="${DEFAULT_ALERTSCRIPTS_PATH}"
    warning "デフォルトパスを使用: ${ALERTSCRIPTS_PATH}"
fi

# ---- 4. スクリプトの配置 ----
info "スクリプトを配置中: ${ALERTSCRIPTS_PATH}"

if [[ ! -d "${ALERTSCRIPTS_PATH}" ]]; then
    info "ディレクトリを作成: ${ALERTSCRIPTS_PATH}"
    mkdir -p "${ALERTSCRIPTS_PATH}"
fi

SCRIPT_DEST="${ALERTSCRIPTS_PATH}/zabbix_notify.py"
cp "${SCRIPT_DIR}/zabbix_notify.py" "${SCRIPT_DEST}"
chmod +x "${SCRIPT_DEST}"

# Zabbix ユーザーが存在する場合はオーナーを変更
if id zabbix &>/dev/null; then
    chown zabbix:zabbix "${SCRIPT_DEST}"
fi

info "スクリプト配置完了: ${SCRIPT_DEST}"

# ---- 5. 設定ファイルの配置 ----
info "設定ファイルを配置中: ${CONFIG_DIR}"

if [[ ! -d "${CONFIG_DIR}" ]]; then
    mkdir -p "${CONFIG_DIR}"
fi

CONFIG_EXAMPLE_SRC="${REPO_ROOT}/config/config.yaml.example"
CONFIG_EXAMPLE_DEST="${CONFIG_DIR}/config.yaml.example"

if [[ -f "${CONFIG_EXAMPLE_SRC}" ]]; then
    cp "${CONFIG_EXAMPLE_SRC}" "${CONFIG_EXAMPLE_DEST}"
    info "設定例ファイルを配置: ${CONFIG_EXAMPLE_DEST}"
else
    warning "config.yaml.example が見つかりません: ${CONFIG_EXAMPLE_SRC}"
fi

CONFIG_DEST="${CONFIG_DIR}/config.yaml"
if [[ ! -f "${CONFIG_DEST}" ]]; then
    if [[ -f "${CONFIG_EXAMPLE_DEST}" ]]; then
        cp "${CONFIG_EXAMPLE_DEST}" "${CONFIG_DEST}"
        info "設定ファイルを作成（編集が必要）: ${CONFIG_DEST}"
    fi
else
    info "既存の設定ファイルを保持: ${CONFIG_DEST}"
fi

# Zabbix ユーザーが存在する場合はオーナーを変更
if id zabbix &>/dev/null; then
    chown -R zabbix:zabbix "${CONFIG_DIR}" 2>/dev/null || true
fi

# ---- 6. 動作確認コマンドの表示 ----
echo ""
echo "========================================"
info "インストール完了"
echo "========================================"
echo ""
echo "次のステップ:"
echo ""
echo "1. Webhook URL を設定する:"
echo "   sudo vi ${CONFIG_DEST}"
echo "   または: export GCHAT_WEBHOOK_URL='https://chat.googleapis.com/v1/spaces/...'"
echo ""
echo "2. 動作確認:"
echo "   sudo -u zabbix ${PYTHON_CMD} ${SCRIPT_DEST} \\"
echo "     \"\" \"テスト\" \\"
echo "     \"ALERT_TYPE=PROBLEM"$'\n'"HOST_NAME=test-server"$'\n'"TRIGGER_NAME=テストアラート"$'\n'"TRIGGER_SEVERITY=High"$'\n'"EVENT_ID=99999"$'\n'"EVENT_DATE=2026.01.01"$'\n'"EVENT_TIME=00:00:00\""
echo ""
echo "3. Zabbix のメディアタイプを設定する:"
echo "   詳細は docs/QUICKSTART.md を参照"
echo ""
