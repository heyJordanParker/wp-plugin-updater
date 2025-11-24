# WP Plugin Updater

Automate WordPress plugin and theme updates in CI/CD pipelines. Supports both WordPress.org plugins and premium plugins using the WooCommerce Software Licensing API.

## Features

- Check for updates from WordPress.org
- Check for updates from WooCommerce Software Licensing API
- Download and commit plugin versions to git branches
- Merge multiple plugin branches
- Designed for GitHub Actions and other CI/CD environments

## Installation

```bash
pip install git+https://github.com/heyJordanParker/wp-plugin-updater.git
```

## Commands

### Check WordPress.org for updates
```bash
wp-plugin check-wordpress-org <slug>
# Example: wp-plugin check-wordpress-org woocommerce
# Returns: {"version": "8.5.2", "download_url": "https://..."}
```

### Download from WordPress.org
```bash
wp-plugin download-wordpress <slug> <version> <branch>
# Example: wp-plugin download-wordpress woocommerce 8.5.2 main
```

Downloads the plugin, extracts it, commits to the specified branch, and pushes to origin.

### Check license API for updates

For premium plugins using WooCommerce Software Licensing API:

```bash
wp-plugin check-license <api_url> <license_key> <plugin_basename> <product_name> <email> <domain> <instance>
# Returns: {"version": "2.1.0", "download_url": "https://..."}
```

**Parameters:**
- `api_url`: License API endpoint (e.g., `https://example.com/?wc-api=upgrade-api&request=pluginupdatecheckall`)
- `license_key`: Your license key
- `plugin_basename`: Plugin basename (e.g., `plugin-premium/plugin-premium.php`)
- `product_name`: Human-readable product name (e.g., `Plugin Premium`)
- `email`: License email
- `domain`: Your site domain (e.g., `https://yoursite.com`)
- `instance`: Site+plugin-specific instance ID from WordPress database

**Getting the instance ID:**

The instance is a unique identifier for each plugin on each WordPress site. For plugins using WooCommerce Software Licensing, retrieve it from your WordPress database:

```bash
wp option get {vendor}_plugins_info --format=json
```

Look for your plugin's SHA1 hash in the output and copy the `instance` value. The hash is computed from the plugin basename.

### Download licensed plugin
```bash
wp-plugin download-licensed <download_url> <branch>
# Example: wp-plugin download-licensed "https://s3.amazonaws.com/..." premium-branch
```

Downloads the licensed plugin, extracts it, commits to the specified branch, and pushes to origin.

### Merge multiple branches
```bash
wp-plugin merge <branch1> <branch2> [branch3...] [--target=branch] [--no-push]
# Example: wp-plugin merge base-plugin premium-addon --target=combined
# Example: wp-plugin merge v1 v2 v3 --no-push  # Merge to working directory without committing
```

Merges multiple plugin branches. The first branch is used as the base, with subsequent branches overlaid on top. Use `--no-push` to merge into working directory without committing (useful for creating PRs).

## Usage in GitHub Actions

Automate plugin updates on a schedule:

```yaml
name: Update Plugin

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Setup Git
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"

      - name: Install updater
        run: |
          sudo apt-get update
          sudo apt-get install -y jq
          pip3 install git+https://github.com/heyJordanParker/wp-plugin-updater.git

      - name: Check for updates
        id: check
        run: |
          INFO=$(wp-plugin check-wordpress-org my-plugin)
          VERSION=$(echo "$INFO" | jq -r '.version')
          echo "version=$VERSION" >> $GITHUB_OUTPUT

      - name: Download and commit
        if: steps.check.outputs.version
        run: |
          wp-plugin download-wordpress my-plugin ${{ steps.check.outputs.version }} main
```

## Use Cases

- **Version Control**: Track plugin versions in git for rollback capability
- **Git Submodules**: Use plugins as submodules in WordPress projects
- **Automated Testing**: Test new plugin versions automatically before deployment
- **Multi-Site Management**: Keep multiple WordPress sites in sync with plugin versions
- **Premium Plugins**: Automate updates for commercial plugins using WooCommerce Software Licensing

## Development

```bash
# Clone the repository
git clone https://github.com/heyJordanParker/wp-plugin-updater.git
cd wp-plugin-updater

# Install in editable mode
pip install -e .

# Run commands
wp-plugin --help
```

## License

MIT License - see [LICENSE](LICENSE) file for details.
