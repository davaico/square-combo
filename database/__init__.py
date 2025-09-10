import logging

from database.database import init_db

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Creating database and tables...")
    init_db()
    logger.info("Finished creating database and tables")