
import os
try:
    with open('backend/ira/server.py', 'r') as f:
        print(f.read())
except Exception as e:
    print(f"Error reading file: {e}")
