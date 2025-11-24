"""Command-line interface for wp-plugin updater."""

import sys
import json
from . import wordpress, license_api, merge


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: wp-plugin <command> [args...]", file=sys.stderr)
        print("\nCommands:", file=sys.stderr)
        print("  check-wordpress-org <slug>", file=sys.stderr)
        print("  download-wordpress <slug> <version> <branch>", file=sys.stderr)
        print("  check-license <api_url> <license_key> <plugin_basename> <product_name> <email> <domain> <instance>", file=sys.stderr)
        print("  download-licensed <url> <branch>", file=sys.stderr)
        print("  merge <free_branch> <pro_branch> <target_branch>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "check-wordpress-org":
            result = wordpress.check_wordpress_org(sys.argv[2])
            print(json.dumps(result))

        elif command == "download-wordpress":
            wordpress.download_wordpress_plugin(sys.argv[2], sys.argv[3], sys.argv[4])

        elif command == "check-license":
            result = license_api.check_license(
                sys.argv[2],  # api_url
                sys.argv[3],  # license_key
                sys.argv[4],  # plugin_basename
                sys.argv[5],  # product_name
                sys.argv[6],  # email
                sys.argv[7],  # domain
                sys.argv[8]   # instance
            )
            print(json.dumps(result))

        elif command == "download-licensed":
            license_api.download_licensed_plugin(sys.argv[2], sys.argv[3])

        elif command == "merge":
            merge.merge_branches(sys.argv[2], sys.argv[3], sys.argv[4])

        else:
            print(f"Unknown command: {command}", file=sys.stderr)
            sys.exit(1)

    except IndexError:
        print(f"Missing arguments for command: {command}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
