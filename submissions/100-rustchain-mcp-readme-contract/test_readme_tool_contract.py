from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
SERVER = (ROOT / "rustchain_mcp" / "server.py").read_text(encoding="utf-8")


def test_readme_bounty_example_matches_registered_tool_contract():
    assert "get_bounties(" not in README
    assert "bounty_search(min_rtc=100)" in README
    assert 'result["bounties"]' in README
    assert "bounty['rtc_reward']" in README

    # Keep the example anchored to the actual registered tool signature.
    assert "def bounty_search(" in SERVER
    assert "min_rtc: float = 0" in SERVER


def test_readme_bottube_heading_matches_listed_tools():
    section = README.split("### BoTTube Platform", 1)[1].split(
        "### Beacon Messaging", 1
    )[0]
    heading = re.search(r"\((\d+) tools\)", "### BoTTube Platform" + section)
    assert heading is not None

    listed_tools = re.findall(r"^- `bottube_[^`]+`", section, re.MULTILINE)
    assert int(heading.group(1)) == len(listed_tools)
    assert len(listed_tools) == 7
