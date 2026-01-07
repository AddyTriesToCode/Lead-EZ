import logging
import sys
from pathlib import Path

# Create logs directory
log_dir = Path("storage/logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / "app.log")
    ]
)

logger = logging.getLogger("leadez")
