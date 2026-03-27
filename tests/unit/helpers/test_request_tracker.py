import pytest

from app.helpers.request_tracker import RequestTracker, _get_current_rss_mb


class TestRequestTracker:

    @pytest.mark.unit
    def test_total(self):
        RequestTracker.custom_active = 3
        RequestTracker.code_active = 5
        assert RequestTracker.total() == 8
        RequestTracker.custom_active = 0
        RequestTracker.code_active = 0

    @pytest.mark.unit
    def test_summary(self):
        RequestTracker.custom_active = 2
        RequestTracker.code_active = 4
        assert RequestTracker.summary() == "custom=2 code=4 total=6"
        RequestTracker.custom_active = 0
        RequestTracker.code_active = 0

    @pytest.mark.unit
    def test_log_output(self, capsys):
        RequestTracker.custom_active = 1
        RequestTracker.code_active = 0
        RequestTracker.log("MEM", "TEST", "extra=data")
        captured = capsys.readouterr()
        assert "[MEM] TEST" in captured.out
        assert "rss=" in captured.out
        assert "maxrss=" in captured.out
        assert "extra=data" in captured.out
        RequestTracker.custom_active = 0

    @pytest.mark.unit
    def test_get_current_rss_mb_returns_positive(self):
        rss = _get_current_rss_mb()
        assert rss > 0
