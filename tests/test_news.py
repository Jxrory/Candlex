from datetime import datetime
from fastapi.testclient import TestClient
from src.main import app
from src.schemas.schemas import NewsRecord

client = TestClient(app)


def test_news_record_defaults():
    r = NewsRecord(
        symbol="SH.600519",
        title="Test title",
        content="Test content",
        url="http://example.com/news/1",
    )
    assert r.symbol == "SH.600519"
    assert r.title == "Test title"
    assert r.content == "Test content"
    assert r.url == "http://example.com/news/1"
    assert r.publish_time is None
    assert r.source_name is None


def test_news_record_full():
    r = NewsRecord(
        symbol="SH.600519",
        title="Title",
        content="Content",
        publish_time=datetime(2026, 5, 20, 10, 30, 0),
        source_name="\u6bcf\u65e5\u7ecf\u6d4e\u65b0\u95fb",
        url="http://example.com/news/1",
    )
    assert r.publish_time == datetime(2026, 5, 20, 10, 30, 0)
    assert r.source_name == "\u6bcf\u65e5\u7ecf\u6d4e\u65b0\u95fb"


def test_news_route_no_refresh():
    resp = client.get("/news/SH.600519")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        item = data[0]
        assert "symbol" in item
        assert "title" in item
        assert "content" in item
        assert "url" in item
