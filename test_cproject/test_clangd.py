#!/usr/bin/env python3
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from code_audit_agent.utils.lsp_client import LSPClient


def test_clangd():
    project_root = "/Users/lometsj/Documents/llm_tool/code_audit/test_cproject"
        
    client = LSPClient(workspace_root=project_root)
    
    print("\n" + "="*60)
    print("Test 1: Start and Initialize clangd")
    print("="*60)
    
    if not client.start():
        print("[FAILED] Failed to start clangd")
        return
    
    print(f"[+] clangd started with PID: {client.process.pid}")
    
    if not client.initialize():
        print("[FAILED] Failed to initialize clangd")
        return
    
    print("[SUCCESS] clangd initialized successfully!")
    
    print("\n" + "="*60)
    print("Test 2: Open text document")
    print("="*60)
    
    main_c_path = os.path.join(project_root, "main.c")
    
    if not client.open_document(main_c_path, language_id="c"):
        print("[FAILED] Failed to open document")
        return
    
    print("[SUCCESS] Document opened")
    
    time.sleep(2)
    
    print("\n" + "="*60)
    print("Test 3: Request definition (goto definition)")
    print("="*60)
    
    definition = client.get_definition(main_c_path, line=52, character=10)
    
    if definition:
        print(f"[SUCCESS] Definition found!")
        print(json.dumps(definition, indent=2))
    else:
        print(f"[INFO] No definition found at this position")
    
    print("\n" + "="*60)
    print("Test 4: Request hover information")
    print("="*60)
    
    hover = client.get_hover(main_c_path, line=30, character=36)
    
    if hover:
        print(f"[SUCCESS] Hover information retrieved!")
        print(json.dumps(hover, indent=2))
    else:
        print(f"[INFO] No hover information at this position")
    
    print("\n" + "="*60)
    print("Test 5: Request references")
    print("="*60)
    
    references = client.get_references(main_c_path, line=30, character=36)
    
    if references:
        print(f"[SUCCESS] References found!")
        print(json.dumps(references, indent=2))
    else:
        print(f"[INFO] No references found at this position")
    
    print("\n" + "="*60)
    print("Test 6: Request document symbols")
    print("="*60)
    
    symbols = client.get_document_symbols(main_c_path)
    
    if symbols:
        print(f"[SUCCESS] Document symbols retrieved! Count: {len(symbols)}")
        for symbol in symbols[:5]:
            print(f"  - {symbol.get('name')} (kind={symbol.get('kind')})")
        if len(symbols) > 5:
            print(f"  ... and {len(symbols) - 5} more")
    else:
        print(f"[INFO] No document symbols found")
    
    print("\n" + "="*60)
    print("Test 7: Shutdown")
    print("="*60)
    
    client.stop()
    print(f"[SUCCESS] clangd exited with code: {client.process.returncode}")
    print("\n[SUCCESS] All tests completed!")


if __name__ == "__main__":
    test_clangd()
