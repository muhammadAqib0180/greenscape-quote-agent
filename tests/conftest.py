import os

# Set test environment variables BEFORE any application modules are imported.
# This ensures that all tests run 100% offline using the in-memory fake database (db_fake.py),
# preventing accidental live calls to Supabase or external APIs.
os.environ["APP_ENV"] = "test"
os.environ.setdefault("GEMINI_API_KEY", "fake-test-key")
os.environ.setdefault("RENDER_THRESHOLD", "30000")
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
