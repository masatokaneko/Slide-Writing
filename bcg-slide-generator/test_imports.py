import sys
print("Python version:", sys.version)
print("\nTesting imports...")

try:
    from flask import Flask
    print("✓ Flask imported successfully")
except Exception as e:
    print("✗ Flask import error:", e)

try:
    from flask_cors import CORS
    print("✓ Flask-CORS imported successfully")
except Exception as e:
    print("✗ Flask-CORS import error:", e)

try:
    from database.db_manager import DatabaseManager
    print("✓ DatabaseManager imported successfully")
except Exception as e:
    print("✗ DatabaseManager import error:", e)

try:
    from core.design_analyzer import DesignAnalyzer
    print("✓ DesignAnalyzer imported successfully")
except Exception as e:
    print("✗ DesignAnalyzer import error:", e)

try:
    from core.content_generator import ContentGenerator
    print("✓ ContentGenerator imported successfully")
except Exception as e:
    print("✗ ContentGenerator import error:", e)

try:
    from core.pptx_generator import PPTXGenerator
    print("✓ PPTXGenerator imported successfully")
except Exception as e:
    print("✗ PPTXGenerator import error:", e)

print("\nTesting Flask app...")
try:
    app = Flask(__name__)
    
    @app.route('/test')
    def test():
        return "Test successful!"
    
    print("✓ Flask app created successfully")
    print("\nStarting test server on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True)
except Exception as e:
    print("✗ Flask app error:", e)
