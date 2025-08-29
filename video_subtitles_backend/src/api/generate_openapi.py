import asyncio
import json
import os
from typing import Any, Dict

from src.api.main import app


async def generate() -> Dict[str, Any]:
    """Dump OpenAPI schema."""
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
