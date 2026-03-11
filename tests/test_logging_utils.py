from pathlib import Path
import re

from one_click_kb_switch.logging_utils import configure_logging


def test_configure_logging_recreates_html_log_file(tmp_path: Path) -> None:
    log_file = tmp_path / "session.html"
    log_file.write_text("stale", encoding="utf-8")

    logger = configure_logging(debug=True, html_log_path=log_file)
    logger.info("fresh message")

    payload = log_file.read_text(encoding="utf-8")
    plain_text = re.sub(r"<[^>]+>", "", payload)
    assert "stale" not in plain_text
    assert "1-Click-KB-Switch session log" in plain_text
