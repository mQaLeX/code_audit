#!/usr/bin/env python3
import os
import sys
import subprocess


def run_test():
    """
    运行代码审计测试
    """
    print("=" * 60)
    print("代码审计Agent - 测试验证")
    print("=" * 60)
    print()
    
    project_dir = os.path.join(os.path.dirname(__file__), "test_project")
    
    if not os.path.exists(project_dir):
        print(f"错误: 测试项目目录不存在: {project_dir}")
        return False
    
    print(f"测试项目目录: {project_dir}")
    print()
    
    print("步骤 1: 检查测试项目文件...")
    app_file = os.path.join(project_dir, "app.py")
    if not os.path.exists(app_file):
        print(f"错误: app.py 不存在")
        return False
    print(f"  ✓ 找到 app.py")
    
    print()
    print("步骤 2: 扫描接口函数...")
    
    try:
        from code_audit_agent.scanners import FunctionScanner
        
        scanner = FunctionScanner()
        functions = scanner.scan_functions(project_dir, "python", "web")
        
        print(f"  ✓ 扫描完成，发现 {len(functions)} 个接口函数")
        
        for i, func in enumerate(functions, 1):
            print(f"    {i}. {func.function_name} ({func.file_path}:{func.line_start})")
    except Exception as e:
        print(f"  ✗ 扫描失败: {str(e)}")
        return False
    
    print()
    print("步骤 3: 运行完整审计（跳过漏洞利用）...")
    
    try:
        result = subprocess.run(
            ["python", "main.py", project_dir, "python", "web", "--skip-exploit", "--verbose"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("  ✓ 审计完成")
        else:
            print(f"  ✗ 审计失败，返回码: {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        print("  ✗ 审计超时")
        return False
    except Exception as e:
        print(f"  ✗ 审计异常: {str(e)}")
        return False
    
    print()
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)
    print()
    print("预期发现的漏洞:")
    print("  - 命令注入漏洞 (3个): ping, exec, search")
    print("  - 任意文件读取漏洞 (3个): read, download, log")
    print()
    print("请检查生成的报告文件以确认漏洞是否被正确识别。")
    
    return True


if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)
