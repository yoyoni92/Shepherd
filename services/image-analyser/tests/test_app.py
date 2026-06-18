import io, pytest
import PIL.Image
import boto3
from moto import mock_aws
from fastapi.testclient import TestClient


@pytest.fixture
def s3_with_image(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("IMAGE_CONFIDENCE_MIN", "0.0")  # always confident
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        # upload a blank image
        buf = io.BytesIO()
        PIL.Image.new("RGB", (224, 224), color=(128, 128, 128)).save(buf, format="JPEG")
        buf.seek(0)
        s3.put_object(Bucket="test-bucket", Key="test/image.jpg", Body=buf.read())
        yield s3


def test_analyse_ok(s3_with_image):
    from app.main import app
    client = TestClient(app)
    resp = client.post("/analyse", json={"s3_key": "test/image.jpg"})
    assert resp.status_code == 200
    data = resp.json()
    assert "doc_type" in data
    assert "confidence" in data
    assert isinstance(data["confidence"], float)


def test_analyse_bad_key(s3_with_image):
    from app.main import app
    client = TestClient(app)
    resp = client.post("/analyse", json={"s3_key": "nonexistent/image.jpg"})
    assert resp.status_code == 400
