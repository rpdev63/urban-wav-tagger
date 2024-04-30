from unittest.mock import MagicMock
from botocore.exceptions import BotoCoreError
import pytest
import os

SOUNDS = ["example.wav", "example.mp3"]


def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Upload" in response.data


@pytest.mark.parametrize("sound", SOUNDS)
def test_upload_file(client, sound):
    with open(os.path.join("tests", sound), "rb") as f:
        data = {
            "file": (f, sound)
        }
        response = client.post(
            "/", data=data, content_type="multipart/form-data")

        assert response.status_code == 302  # Check if redirect happened
        assert "/results?filename=static/tmp/example" in response.location


def test_results_page_success(client):
    # api should must be avalaible
    response = client.get('/results?filename=static/tmp/example.wav')
    assert response.status_code == 200
    assert b"Results" in response.data


def test_validate_result_confirmed_correctly(client, mock_s3_client):
    mock_s3_client.upload_file = MagicMock()
    mock_s3_client.create_bucket = MagicMock()
    mock_s3_client.download_file = MagicMock()

    response = client.post('/validate', data={
        'filename': 'testfile.wav',
        'confirm': 'yes',
        'prediction': 'dog_bark'
    })

    # Check for successful flash message
    with client.session_transaction() as sess:
        assert 'File and tag sent. Thank you!' in sess['_flashes'][0][1]

    # Check that the user is redirected to the upload page
    assert response.status_code == 302
    assert '/' == response.headers['Location']


def test_validate_result_aws_error(client, mock_s3_client):
    mock_s3_client.upload_file = MagicMock(side_effect=BotoCoreError())

    response = client.post('/validate', data={
        'filename': 'testfile.wav',
        'confirm': 'yes',
        'prediction': 'dog_bark'
    })

    # Check for error flash message
    with client.session_transaction() as sess:
        assert 'An AWS error occurred:' in sess['_flashes'][0][1]

    # Check that the user is redirected to the upload page
    assert response.status_code == 302
    assert '/' == response.headers['Location']
