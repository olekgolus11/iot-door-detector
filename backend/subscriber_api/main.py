from __future__ import annotations

import uvicorn

from backend.common.config import SubscriberConfig
from backend.subscriber_api.app import build_app


def main() -> None:
    config = SubscriberConfig()
    uvicorn.run(build_app(config), host=config.api_host, port=config.api_port)


if __name__ == "__main__":
    main()

