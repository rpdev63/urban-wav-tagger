import pytest
from app import app
from unittest.mock import patch


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_s3_client():
    with patch('boto3.client') as mock:
        yield mock()
