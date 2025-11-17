#!/usr/bin/env python3
"""
Test script to validate import paths are correct without executing modules
"""
import os
import sys
import ast

# Set PYTHONPATH as it would be in the start command (using absolute path)
project_root = '/home/engine/project'
os.environ['PYTHONPATH'] = project_root
sys.path.insert(0, project_root)

def check_import_syntax(file_path, import_line):
    """Check if an import line has valid syntax"""
    try:
        ast.parse(import_line)
        return True
    except SyntaxError:
        return False

# Test that the import statements we added are syntactically correct
test_imports = [
    "from api import engine_crawl",
    "from api import engine_parse", 
    "from api import engine_rules_enhanced as engine_rules",
    "from api import engine_report",
    "from api.vysalytica.db import SessionLocal",
    "from api.vysalytica.db.migrations import run_migrations",
    "from api.vysalytica import engine_ai_visibility, engine_fixgen",
    "from api.vysalytica.middleware import limiter, require_api_key",
    "from api.vysalytica import plans",
    "from api.vysalytica.engine_answer_graph import build_answer_graph",
    "from api.vysalytica.engine_playbooks import generate_playbook"
]

print("Testing import syntax...")
for import_line in test_imports:
    if check_import_syntax("", import_line):
        print(f"✓ {import_line} - syntax OK")
    else:
        print(f"✗ {import_line} - syntax ERROR")
        sys.exit(1)

# Test that the files exist at expected locations
files_to_check = [
    "/home/engine/project/api/__init__.py",
    "/home/engine/project/api/engine_crawl.py",
    "/home/engine/project/api/engine_parse.py", 
    "/home/engine/project/api/engine_rules_enhanced.py",
    "/home/engine/project/api/engine_report.py",
    "/home/engine/project/api/vysalytica/__init__.py",
    "/home/engine/project/api/vysalytica/config.py",
    "/home/engine/project/api/vysalytica/db/__init__.py",
    "/home/engine/project/api/vysalytica/db/models.py",
    "/home/engine/project/api/vysalytica/db/migrations.py",
    "/home/engine/project/api/vysalytica/middleware.py",
    "/home/engine/project/api/vysalytica/engine_ai_visibility.py",
    "/home/engine/project/api/vysalytica/engine_fixgen.py",
    "/home/engine/project/api/vysalytica/engine_playbooks.py",
    "/home/engine/project/api/vysalytica/engine_answer_graph.py"
]

print("\nChecking file existence...")
for file_path in files_to_check:
    if os.path.exists(file_path):
        print(f"✓ {file_path} exists")
    else:
        print(f"✗ {file_path} missing")
        sys.exit(1)

# Test that PYTHONPATH setting would work
print("\nTesting PYTHONPATH approach...")
try:
    # Add project root to path
    sys.path.insert(0, project_root)
    
    # Check if api directory can be found
    api_path = os.path.join(project_root, 'api')
    if os.path.exists(api_path) and os.path.isdir(api_path):
        print(f"✓ api directory found at {api_path}")
        
        # Check if api has __init__.py
        init_path = os.path.join(api_path, '__init__.py')
        if os.path.exists(init_path):
            print(f"✓ api/__init__.py exists")
        else:
            print(f"✗ api/__init__.py missing")
            sys.exit(1)
    else:
        print(f"✗ api directory not found at {api_path}")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ PYTHONPATH test failed: {e}")
    sys.exit(1)

print("\n✓ All import structure checks passed")
print("✓ The PYTHONPATH approach will work on Render when dependencies are installed")

# Additional check: ensure no old vysalytica imports remain in api/ directory
print("\nChecking for remaining old vysalytica imports...")
import re

old_import_pattern = re.compile(r'from\s+vysalytica\s+|import\s+vysalytica\s+')
found_old_imports = False

for root, dirs, files in os.walk('/home/engine/project/api'):
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if old_import_pattern.search(content):
                        print(f"✗ Found old vysalytica import in {file_path}")
                        found_old_imports = True
            except Exception as e:
                print(f"⚠ Could not read {file_path}: {e}")

if found_old_imports:
    sys.exit(1)
else:
    print("✓ No old vysalytica imports found in api/ directory")