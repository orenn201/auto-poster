import os

print("✅ Hello from Python!")
print("Current working directory:", os.getcwd())
print("Python executable:", os.sys.executable)
print("Environment variables:")
for var in ("WP_URL","WP_USER","WP_PASSWORD","OPENAI_API_KEY"):
    print(f"  {var} =", os.getenv(var))
