"""Command-line interface for wp-plugin updater."""

import sys
import json
from . import wordpress, license_api, merge, composer, version


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: wp-plugin <command> [args...]", file=sys.stderr)
        print("\nCommands:", file=sys.stderr)
        print("  check-wordpress-org <slug>", file=sys.stderr)
        print("  download-wordpress <slug> <version> <branch>", file=sys.stderr)
        print("  check-license <api_url> <license_key> <plugin_basename> <product_name> <email> <domain> <instance>", file=sys.stderr)
        print("  download-licensed <url> <branch>", file=sys.stderr)
        print("  merge <branch1> <branch2> [branch3...] [--target=branch] [--no-push]", file=sys.stderr)
        print("  generate-composer <name> <version> <type> [--vendor=creatorincome] [--description=...]", file=sys.stderr)
        print("  is-newer <candidate> <current>", file=sys.stderr)
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
            # Parse branches and flags
            branches = []
            target = None
            push = True

            for arg in sys.argv[2:]:
                if arg.startswith('--target='):
                    target = arg.split('=', 1)[1]
                elif arg == '--no-push':
                    push = False
                elif not arg.startswith('--'):
                    branches.append(arg)

            if len(branches) < 2:
                print("Error: Need at least 2 branches to merge", file=sys.stderr)
                sys.exit(1)

            merge.merge(branches, target=target, push=push)

        elif command == "generate-composer":
            # Parse args: name, package_version, type, then optional flags
            name = sys.argv[2]
            package_version = sys.argv[3]
            package_type = sys.argv[4]
            vendor = "creatorincome"
            description = None

            for arg in sys.argv[5:]:
                if arg.startswith('--vendor='):
                    vendor = arg.split('=', 1)[1]
                elif arg.startswith('--description='):
                    description = arg.split('=', 1)[1]

            composer.write_composer_json(name, package_version, package_type, description, vendor)
            print(f"Generated composer.json for {vendor}/{name} v{package_version}", file=sys.stderr)

        elif command == "is-newer":
            candidate = sys.argv[2]
            current = sys.argv[3]
            result = version.is_newer(candidate, current)
            print(json.dumps({"is_newer": result, "candidate": candidate, "current": current}))

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
