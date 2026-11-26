import json
from pathlib import Path


def test_teleop_takes_over_hands_back_and_records_mcap(run_script):
    out = run_script("demo.py", "--seconds", "8", "--json", cwd=Path(__file__).parent)
    report = json.loads(out)
    assert all(report["checks"].values()), report["checks"]
    assert report["checks"]["takeover"] and report["checks"]["hand_back"]
    holders = [lease["holder"] for lease in report["lease_timeline"] if lease["holder"]]
    assert holders[0] == "policy" and "operator" in holders and holders[-1] == "policy"
    topics = report["recording"]["summary"]["topics"]
    assert topics["/ur10e/wrist/cam"]["messages"] > 0
    assert topics["/ur10e/arm/_applied"]["messages"] > 1000
