import pytest
from unittest.mock import MagicMock, patch
from selisih import ojk

def test_clean_html_text():
    html = "<a href='#'>Peraturan <b>OJK</b> Nomor 22</a>"
    assert ojk._clean_html_text(html) == "Peraturan OJK Nomor 22"
    assert ojk._clean_html_text("") == ""

def test_extract_detail_url():
    html = "<a href='/Web/ViewPeraturan/Detail/123/10/06'>Judul</a>"
    url = ojk._extract_detail_url(html)
    assert url == "https://jdih.ojk.go.id/Web/ViewPeraturan/Detail/123/10/06"

def test_fetch_ojk_regulations_mocked():
    sample_response = {
        "aaData": [
            [
                "<a href='/Web/ViewPeraturan/Detail/abc-123/10/06'>POJK Nomor 22 Tahun 2023</a>",
                "22",
                "ITSK",
                None,
                None,
                "Peraturan OJK",
                "01-01-2024",
                "Berlaku"
            ]
        ]
    }
    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_response
        mock_get.return_value = mock_resp

        results = ojk.fetch_ojk_regulations(sectors=["10"])
        assert len(results) == 1
        item = results[0]
        assert item["nomor"] == "22"
        assert item["tahun"] == "2023"
        assert item["id"] == "abc-123"
        assert item["status"] == "Berlaku"
