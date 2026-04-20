import os

from cryptography.fernet import Fernet

os.environ["FERNET_KEY"] = Fernet.generate_key().decode()
os.environ["SESSION_SECRET"] = "test-secret-test-secret-test-secret-test"
os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
