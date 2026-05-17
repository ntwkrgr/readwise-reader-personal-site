import os

from app import create_app
from app.shared import READWISE_TOKEN

app = create_app()


if __name__ == "__main__":
    if not READWISE_TOKEN:
        print("WARNING: READWISE_TOKEN not set. Create a .env file — see .env.example")
    port = int(os.environ.get("PORT", 5555))
    app.run(host="0.0.0.0", port=port, debug=True)
