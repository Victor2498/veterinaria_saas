from src.core.security import get_password_hash

try:
    print("Testing hash...")
    h = get_password_hash("admin123456")
    print(f"Hash generated: {h[:10]}...")
except Exception as e:
    print(f"Error: {e}")
