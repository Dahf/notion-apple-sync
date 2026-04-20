from app.notion_oauth import authorize_url


def test_authorize_url_contains_params():
    url = authorize_url("my-state-123")
    assert url.startswith("https://api.notion.com/v1/oauth/authorize?")
    assert "state=my-state-123" in url
    assert "response_type=code" in url
    assert "owner=user" in url
