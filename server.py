import sys
import uvicorn
from pathlib import Path

# Add src to path for package imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    """Start the FastAPI server."""
    from api.main import app
    
    # Run the server
    import os
    port = int(os.getenv("PORT", 5009))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
