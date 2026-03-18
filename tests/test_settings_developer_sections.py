import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))



def test_event_console_entrypoint_is_present_in_developer_settings_template():
    dev_template_path = (
        PROJECT_ROOT
        / "webui"
        / "components"
        / "settings"
        / "developer"
        / "dev.html"
    )
    content = dev_template_path.read_text(encoding="utf-8")
    assert "websocket-event-console.html" in content
    assert "!$store.settings.additional?.is_dockerized" in content
