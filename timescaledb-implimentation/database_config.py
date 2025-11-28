import os
import psycopg2
from dotenv import load_dotenv
# Load the specific env file provided by the user
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, 'tiger-cloud-db-36044-credentials.env')
load_dotenv(env_path)


def get_db_connection():
    """Establishes and returns a connection to the TimescaleDB database."""
    try:
        service_url = os.environ.get("TIMESCALE_SERVICE_URL")
        if not service_url:
            raise ValueError(
                "TIMESCALE_SERVICE_URL not found in environment variables.")

        conn = psycopg2.connect(service_url)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise
