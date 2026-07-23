
import os

server_path = 'backend/ira/server.py'
if os.path.exists(server_path):
    with open(server_path, 'r') as f:
        print(f.read())
else:
    print(f"File {server_path} not found.")
