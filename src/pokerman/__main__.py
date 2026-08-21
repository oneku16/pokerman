import os

import uvicorn

from pokerman.presentation.api.app import create_app

app = create_app()


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
