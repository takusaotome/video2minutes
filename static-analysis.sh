#!/bin/bash

# Video2Minutes 静的コード解析スクリプト
# Python と JavaScript/Vue.js の包括的な静的解析を実行

set -e

# 色付きログ用の関数
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${PURPLE}=== $1 ===${NC}\n"
}

# エラーカウンター
PYTHON_ERRORS=0
JS_ERRORS=0
TOTAL_ERRORS=0

# 結果ディレクトリの作成
mkdir -p reports/static-analysis
REPORT_DIR="reports/static-analysis"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

log_section "Video2Minutes 静的コード解析開始"
log_info "タイムスタンプ: $TIMESTAMP"
log_info "レポート出力先: $REPORT_DIR"

# ===== Python 静的解析 =====
log_section "Python 静的解析"

# 1. Black (コードフォーマット)
log_info "Black によるコードフォーマットチェック..."
if python -m black --check --diff src/backend/ tests/ > "$REPORT_DIR/black_$TIMESTAMP.txt" 2>&1; then
    log_success "Black: フォーマットOK"
else
    log_warning "Black: フォーマット修正が必要"
    PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
fi

# 2. isort (import順序)
log_info "isort による import 順序チェック..."
if python -m isort --check-only --diff src/backend/ tests/ > "$REPORT_DIR/isort_$TIMESTAMP.txt" 2>&1; then
    log_success "isort: import順序OK"
else
    log_warning "isort: import順序修正が必要"
    PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
fi

# 3. Flake8 (PEP8準拠)
log_info "Flake8 による PEP8 準拠チェック..."
if python3 -m flake8 src/backend/ tests/ --output-file="$REPORT_DIR/flake8_$TIMESTAMP.txt" --tee; then
    log_success "Flake8: PEP8準拠OK"
else
    log_error "Flake8: PEP8違反あり"
    PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
fi

# 4. MyPy (型チェック)
log_info "MyPy による型チェック..."
if python3 -m mypy src/backend/ > "$REPORT_DIR/mypy_$TIMESTAMP.txt" 2>&1; then
    log_success "MyPy: 型チェックOK"
else
    log_error "MyPy: 型エラーあり"
    PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
fi

# 5. Pylint (コード品質)
log_info "Pylint によるコード品質チェック..."
if python3 -m pylint src/backend/ --output-format=text > "$REPORT_DIR/pylint_$TIMESTAMP.txt" 2>&1; then
    log_success "Pylint: コード品質OK"
else
    log_warning "Pylint: 改善点あり"
    PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
fi

# 6. Bandit (セキュリティ)
log_info "Bandit によるセキュリティチェック..."
if python3 -m bandit -r src/backend/ -f txt -o "$REPORT_DIR/bandit_$TIMESTAMP.txt"; then
    log_success "Bandit: セキュリティOK"
else
    log_error "Bandit: セキュリティ問題あり"
    PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
fi

# 7. Safety (依存関係脆弱性)
log_info "Safety による依存関係脆弱性チェック..."
if python3 -m safety check --output text > "$REPORT_DIR/safety_$TIMESTAMP.txt" 2>&1; then
    log_success "Safety: 依存関係OK"
else
    log_error "Safety: 脆弱性あり"
    PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
fi

# ===== JavaScript/Vue.js 静的解析 =====
log_section "JavaScript/Vue.js 静的解析"

# フロントエンド解析
log_info "フロントエンドコードの解析..."
cd src/frontend

# 1. ESLint (コード品質・スタイル)
log_info "ESLint によるコード品質チェック..."
if npx eslint src/ --ext .js,.vue,.ts --format=json --output-file="../../$REPORT_DIR/eslint_frontend_$TIMESTAMP.json"; then
    log_success "ESLint (Frontend): コード品質OK"
else
    log_error "ESLint (Frontend): 問題あり"
    JS_ERRORS=$((JS_ERRORS + 1))
fi

# 2. Prettier (フォーマット)
log_info "Prettier によるフォーマットチェック..."
if npx prettier --check src/ > "../../$REPORT_DIR/prettier_frontend_$TIMESTAMP.txt" 2>&1; then
    log_success "Prettier (Frontend): フォーマットOK"
else
    log_warning "Prettier (Frontend): フォーマット修正が必要"
    JS_ERRORS=$((JS_ERRORS + 1))
fi

cd ../..

# テストコード解析
log_info "テストコードの解析..."
cd tests/unit-js

# 3. ESLint (テストコード)
log_info "ESLint によるテストコード品質チェック..."
if npx eslint . --ext .js,.vue,.ts --format=json --output-file="../../$REPORT_DIR/eslint_tests_$TIMESTAMP.json"; then
    log_success "ESLint (Tests): テストコード品質OK"
else
    log_error "ESLint (Tests): 問題あり"
    JS_ERRORS=$((JS_ERRORS + 1))
fi

# 4. Prettier (テストコード)
log_info "Prettier によるテストコードフォーマットチェック..."
if npx prettier --check . > "../../$REPORT_DIR/prettier_tests_$TIMESTAMP.txt" 2>&1; then
    log_success "Prettier (Tests): フォーマットOK"
else
    log_warning "Prettier (Tests): フォーマット修正が必要"
    JS_ERRORS=$((JS_ERRORS + 1))
fi

cd ../..

# ===== 結果集計とレポート生成 =====
log_section "解析結果集計"

TOTAL_ERRORS=$((PYTHON_ERRORS + JS_ERRORS))

# HTML レポート生成
cat > "$REPORT_DIR/summary_$TIMESTAMP.html" << EOF
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video2Minutes 静的解析レポート - $TIMESTAMP</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; }
        .section { margin: 20px 0; padding: 15px; border-left: 4px solid #667eea; background: #f8f9fa; }
        .success { border-left-color: #28a745; }
        .warning { border-left-color: #ffc107; }
        .error { border-left-color: #dc3545; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat-card { flex: 1; padding: 15px; text-align: center; border-radius: 8px; }
        .stat-python { background: #3776ab; color: white; }
        .stat-js { background: #f7df1e; color: black; }
        .stat-total { background: #6c757d; color: white; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; }
        .file-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }
        .file-item { padding: 10px; background: white; border: 1px solid #dee2e6; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Video2Minutes 静的解析レポート</h1>
        <p>実行日時: $TIMESTAMP</p>
    </div>

    <div class="stats">
        <div class="stat-card stat-python">
            <h3>Python エラー</h3>
            <h2>$PYTHON_ERRORS</h2>
        </div>
        <div class="stat-card stat-js">
            <h3>JavaScript エラー</h3>
            <h2>$JS_ERRORS</h2>
        </div>
        <div class="stat-card stat-total">
            <h3>総エラー数</h3>
            <h2>$TOTAL_ERRORS</h2>
        </div>
    </div>

    <div class="section">
        <h2>🐍 Python 解析結果</h2>
        <div class="file-list">
            <div class="file-item">
                <h4>Black (フォーマット)</h4>
                <p><a href="black_$TIMESTAMP.txt">レポートを見る</a></p>
            </div>
            <div class="file-item">
                <h4>isort (Import順序)</h4>
                <p><a href="isort_$TIMESTAMP.txt">レポートを見る</a></p>
            </div>
            <div class="file-item">
                <h4>Flake8 (PEP8準拠)</h4>
                <p><a href="flake8_$TIMESTAMP.txt">レポートを見る</a></p>
            </div>
            <div class="file-item">
                <h4>MyPy (型チェック)</h4>
                <p><a href="mypy_$TIMESTAMP.txt">レポートを見る</a></p>
            </div>
            <div class="file-item">
                <h4>Pylint (コード品質)</h4>
                <p><a href="pylint_$TIMESTAMP.txt">レポートを見る</a></p>
            </div>
            <div class="file-item">
                <h4>Bandit (セキュリティ)</h4>
                <p><a href="bandit_$TIMESTAMP.txt">レポートを見る</a></p>
            </div>
            <div class="file-item">
                <h4>Safety (脆弱性)</h4>
                <p><a href="safety_$TIMESTAMP.txt">レポートを見る</a></p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>🟨 JavaScript/Vue.js 解析結果</h2>
        <div class="file-list">
            <div class="file-item">
                <h4>ESLint (Frontend)</h4>
                <p><a href="eslint_frontend_$TIMESTAMP.json">レポートを見る</a></p>
            </div>
            <div class="file-item">
                <h4>Prettier (Frontend)</h4>
                <p><a href="prettier_frontend_$TIMESTAMP.txt">レポートを見る</a></p>
            </div>
            <div class="file-item">
                <h4>ESLint (Tests)</h4>
                <p><a href="eslint_tests_$TIMESTAMP.json">レポートを見る</a></p>
            </div>
            <div class="file-item">
                <h4>Prettier (Tests)</h4>
                <p><a href="prettier_tests_$TIMESTAMP.txt">レポートを見る</a></p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>📊 推奨アクション</h2>
        <ul>
            <li>エラー数が0でない場合は、各レポートを確認して修正してください</li>
            <li>定期的に静的解析を実行してコード品質を維持してください</li>
            <li>CI/CDパイプラインに組み込むことを推奨します</li>
        </ul>
    </div>
</body>
</html>
EOF

# コンソール出力
echo ""
log_section "📊 解析結果サマリー"
echo -e "${CYAN}Python エラー数:${NC} $PYTHON_ERRORS"
echo -e "${CYAN}JavaScript エラー数:${NC} $JS_ERRORS"
echo -e "${CYAN}総エラー数:${NC} $TOTAL_ERRORS"
echo ""

if [ $TOTAL_ERRORS -eq 0 ]; then
    log_success "🎉 すべての静的解析をパスしました！"
    echo -e "${GREEN}コード品質は良好です。${NC}"
else
    log_warning "⚠️  修正が必要な項目があります"
    echo -e "${YELLOW}詳細は以下のレポートを確認してください:${NC}"
    echo -e "${CYAN}HTML レポート:${NC} $REPORT_DIR/summary_$TIMESTAMP.html"
fi

echo ""
log_info "すべてのレポートは $REPORT_DIR/ に保存されました"
log_info "HTMLレポートをブラウザで開いて詳細を確認してください"

# 自動修正オプション
echo ""
read -p "自動修正を実行しますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_section "🔧 自動修正実行"
    
    # Python 自動修正
    log_info "Python コードの自動修正..."
    python3 -m black src/backend/ tests/
    python3 -m isort src/backend/ tests/
    python3 -m autopep8 --in-place --recursive src/backend/ tests/
    
    # JavaScript 自動修正
    log_info "JavaScript コードの自動修正..."
    cd src/frontend && npx prettier --write src/ && cd ../..
    cd tests/unit-js && npx prettier --write . && cd ../..
    cd src/frontend && npx eslint src/ --ext .js,.vue,.ts --fix && cd ../..
    cd tests/unit-js && npx eslint . --ext .js,.vue,.ts --fix && cd ../..
    
    log_success "自動修正完了"
fi

exit $TOTAL_ERRORS 