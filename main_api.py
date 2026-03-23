import sys
import uvicorn
from pathlib import Path

# Add src to path for package imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    """Start the FastAPI server."""
    from edu_onboarding.api.main import app
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
