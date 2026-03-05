#!/usr/bin/env python3
"""TUI入口脚本"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from code_audit_agent.tui.app import main


if __name__ == "__main__":
    main()
