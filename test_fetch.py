#!/usr/bin/env python3
import urllib.request
import sys

try:
    response = urllib.request.urlopen(f"http://127.0.0.1:8080/{sys.argv[1]}")
    content = response.read().decode('utf-8')
    print(f"Response length: {len(content)}")
    print(f"Content: {content}")
except Exception as e:
    print(f"Error: {e}")
