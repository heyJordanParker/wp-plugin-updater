"""Composer package generation for WordPress plugins/themes."""

import json
import os


def generate_composer_json(
    name: str,
    version: str,
    package_type: str,
    description: str = None,
    vendor: str = "creatorincome"
) -> dict:
    """
    Generate composer.json content for a WordPress plugin or theme.

    Args:
        name: Package name (e.g., "bricks")
        version: Version string (e.g., "1.11.1")
        package_type: "wordpress-plugin" or "wordpress-theme"
        description: Optional description
        vendor: Composer vendor namespace (default: "creatorincome")

    Returns:
        dict: Composer.json content
    """
    composer = {
        "name": f"{vendor}/{name}",
        "type": package_type,
        "version": version,
        "license": "proprietary"
    }

    if description:
        composer["description"] = description

    return composer


def write_composer_json(
    name: str,
    version: str,
    package_type: str,
    description: str = None,
    vendor: str = "creatorincome",
    path: str = "."
):
    """
    Generate and write composer.json to disk.

    Args:
        name: Package name
        version: Version string
        package_type: "wordpress-plugin" or "wordpress-theme"
        description: Optional description
        vendor: Composer vendor namespace
        path: Directory to write to (default: current directory)
    """
    composer = generate_composer_json(name, version, package_type, description, vendor)
    file_path = os.path.join(path, "composer.json")

    with open(file_path, "w") as f:
        json.dump(composer, f, indent=2)
        f.write("\n")
