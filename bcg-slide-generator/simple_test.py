from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket

# ポートが使用可能か確認
def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

print("Checking port 8080...")
if check_port(8080):
    print("Port 8080 is already in use!")
else:
    print("Port 8080 is available")

print("\nStarting simple HTTP server on port 8081...")
try:
    server = HTTPServer(('127.0.0.1', 8081), SimpleHTTPRequestHandler)
    print("Server started at http://127.0.0.1:8081")
    print("Press Ctrl+C to stop")
    server.serve_forever()
except Exception as e:
    print(f"Error: {e}")
