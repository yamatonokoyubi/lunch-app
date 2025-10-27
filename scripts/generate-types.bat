@echo off
REM TypeScript型定義生成スクリプト (Windows版)
REM schemas.pyからTypeScript型定義を自動生成します

echo 🔄 Generating TypeScript types from Pydantic schemas...

REM 出力ディレクトリを確認・作成
set OUTPUT_DIR=static\js\types
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM Python仮想環境の確認
if not exist "venv" (
    echo ⚠️  Virtual environment not found. Please create one first:
    echo    python -m venv venv
    echo    venv\Scripts\activate
    echo    pip install -r requirements.txt
    exit /b 1
)

REM 仮想環境をアクティベート
call venv\Scripts\activate.bat

REM pydantic-to-typescriptを使用して型定義を生成
python -c "
import sys
from pathlib import Path
from pydantic_to_typescript import generate_typescript_defs

print('📝 Parsing Pydantic models...')
try:
    generate_typescript_defs('schemas.py', '%OUTPUT_DIR%/api.ts')
    print('✅ TypeScript types generated successfully!')
    print('📁 Output: %OUTPUT_DIR%/api.ts')
except Exception as e:
    print(f'❌ Error generating types: {e}')
    sys.exit(1)
"

if errorlevel 1 (
    echo ❌ Failed to generate types
    exit /b 1
)

REM 生成されたファイルの確認
if exist "%OUTPUT_DIR%\api.ts" (
    echo.
    echo 📊 Generated file info:
    for %%A in ("%OUTPUT_DIR%\api.ts") do echo File size: %%~zA bytes
    echo.
    echo ✨ Type generation completed successfully!
    echo 💡 Remember to commit both schemas.py and %OUTPUT_DIR%\api.ts
) else (
    echo ❌ Failed to generate %OUTPUT_DIR%\api.ts
    exit /b 1
)