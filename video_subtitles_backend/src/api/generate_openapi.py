import asyncio
import json
import os
from typing import Any, Dict

from src.api.main import app, on_startup


async def generate() -> Dict[str, Any]:
    """Ensure startup hooks ran (to build routes consistently), then dump OpenAPI."""
    # Run startup to ensure any dynamic route setup is applied (idempotent)
    await on_startup()
    # Generate schema
    return app.openapi()


def main() -> None:
    # Ensure interfaces directory exists
    output_dir = "interfaces"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "openapi.json")

    schema = asyncio.run(generate())
    # Write schema prettified
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"OpenAPI schema written to {output_path}")


if __name__ == "__main__":
    main()
