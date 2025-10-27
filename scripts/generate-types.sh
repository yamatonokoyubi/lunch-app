#!/bin/bash

# TypeScript型定義生成スクリプト
# schemas.pyからTypeScript型定義を自動生成します

echo "🔄 Generating TypeScript types from Pydantic schemas..."

# 出力ディレクトリを確認・作成
OUTPUT_DIR="static/js/types"
mkdir -p "$OUTPUT_DIR"

# Python仮想環境の確認
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Please create one first:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# 仮想環境をアクティベート（Linux/Mac）
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
# Windows Git Bash用
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "❌ Could not find virtual environment activation script"
    exit 1
fi

# pydantic-to-typescriptを使用して型定義を生成
python -c "
import json
from pathlib import Path
from pydantic_to_typescript import generate_typescript_defs

# schemas.pyから型定義を生成
print('📝 Parsing Pydantic models...')
try:
    generate_typescript_defs('schemas.py', '$OUTPUT_DIR/api.ts')
    print('✅ TypeScript types generated successfully!')
    print('📁 Output: $OUTPUT_DIR/api.ts')
except Exception as e:
    print(f'❌ Error generating types: {e}')
    exit(1)
"

# 生成されたファイルの確認
if [ -f "$OUTPUT_DIR/api.ts" ]; then
    echo ""
    echo "📊 Generated file info:"
    wc -l "$OUTPUT_DIR/api.ts"
    echo ""
    echo "🔍 Preview (first 10 lines):"
    head -10 "$OUTPUT_DIR/api.ts"
    echo ""
    echo "✨ Type generation completed successfully!"
    echo "💡 Remember to commit both schemas.py and $OUTPUT_DIR/api.ts"
else
    echo "❌ Failed to generate $OUTPUT_DIR/api.ts"
    exit 1
fi