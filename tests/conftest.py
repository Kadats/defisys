import os
import pytest
import backend.src.config as config

@pytest.fixture(scope="session", autouse=True)
def override_database_url():
    """
    Override the DATABASE_URL with TEST_DATABASE_URL for all tests.
    This ensures tests never run against the production database.
    """
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if not test_db_url:
        pytest.fail("TEST_DATABASE_URL is not set in the environment.")
    
    # Override both the module-level constant and the settings object
    config.DATABASE_URL = test_db_url
    config._settings.DATABASE_URL = test_db_url
    
    # Also update the environment variable for any other tools that might read it directly
    os.environ["DATABASE_URL"] = test_db_url
