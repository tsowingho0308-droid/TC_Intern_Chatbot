import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

if __name__ == "__main__":
    import uvicorn
    from backend.server import app

    logger = logging.getLogger("main")
    logger.info("Starting Voice Agent server at http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
