from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vtsd_client import VtsdClient


def main() -> None:
    client = VtsdClient()
    print("--- call APIStateRequest ---")
    print(json.dumps(client.call("APIStateRequest", responseMode="data", clientRequestId="test-call"), ensure_ascii=False, indent=2))

    print("--- cast HotkeyTriggerRequest (VTS未接続時はaccepted=false想定) ---")
    print(
        json.dumps(
            client.cast("HotkeyTriggerRequest", {"hotkeyID": "dummy"}, clientRequestId="test-cast"),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
