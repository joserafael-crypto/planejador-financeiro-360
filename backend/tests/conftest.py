import os, sys
from pathlib import Path
os.environ.setdefault('DATABASE_URL','sqlite+pysqlite:///:memory:')
os.environ.setdefault('JWT_SECRET','test-secret-' + 'x'*64)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
