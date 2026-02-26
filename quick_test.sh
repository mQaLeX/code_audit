#!/bin/bash

echo "=========================================="
echo "代码审计Agent - 快速测试"
echo "=========================================="
echo ""

echo "步骤 1: 安装依赖..."
pip install -r requirements.txt -q
echo "✓ 依赖安装完成"
echo ""

echo "步骤 2: 检查环境变量..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠ 警告: OPENAI_API_KEY 环境变量未设置"
    echo "请设置环境变量或在运行时使用 --api-key 参数"
    echo ""
    echo "示例:"
    echo "  export OPENAI_API_KEY=your_api_key"
    echo "  或"
    echo "  python main.py test_project python web --api-key your_api_key"
    echo ""
    read -p "是否继续? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ OPENAI_API_KEY 已设置"
fi
echo ""

echo "步骤 3: 运行代码审计..."
echo ""
python main.py test_project python web --skip-exploit --verbose

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "生成的报告文件位于: code_audit_agent/reports/"

