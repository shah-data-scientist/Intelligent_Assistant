"""Start API server with proper logging."""

import os

# Set environment variables
os.environ["VIRTUAL_ENV"] = os.path.join(os.getcwd(), ".venv")

# Run the API
import uvicorn

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8001, log_level="info", reload=False)
