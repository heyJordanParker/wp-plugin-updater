# WP Plugin Updater

Utilities for automating WordPress plugin and theme updates in CI/CD.

## Installation

```bash
pip install git+https://github.com/heyJordanParker/wp-plugin-updater.git
```

## Commands

### Check WordPress.org for updates
```bash
wp-plugin check-wordpress-org <slug>
# Returns: {"version": "3.13.1.3", "download_url": "https://..."}
```

### Download from WordPress.org
```bash
wp-plugin download-wordpress <slug> <version> <branch>
```

### Check license API for updates
```bash
wp-plugin check-license <api_url> <license_key> <plugin_basename> <product_name> <email> <domain> <instance>
# Returns: {"version": "3.13.3", "download_url": "https://..."}
```

**Parameters:**
- `api_url`: License API endpoint (e.g., `https://license.funnelkit.com/?wc-api=upgrade-api&request=pluginupdatecheckall`)
- `license_key`: Your license key
- `plugin_basename`: Plugin basename (e.g., `funnel-builder-pro/funnel-builder-pro.php`)
- `product_name`: Human-readable product name (e.g., `Funnel Builder Pro`)
- `email`: License email
- `domain`: Your site domain (e.g., `https://example.com`)
- `instance`: Site+plugin-specific instance ID from WordPress database

**Getting the instance ID:**
The instance is a unique identifier for each plugin on each WordPress site. To retrieve it:
```bash
wp option get woofunnels_plugins_info --format=json
```
Look for your plugin's hash in the output and copy the `instance` value.

### Download licensed plugin
```bash
wp-plugin download-licensed <download_url> <branch>
```

### Merge free and pro branches
```bash
wp-plugin merge <free_branch> <pro_branch> <target_branch>
```

## Usage in GitHub Actions

```yaml
- name: Install updater
  run: pip install git+https://github.com/heyJordanParker/wp-plugin-updater.git

- name: Check for updates
  run: wp-plugin check-wordpress-org funnel-builder
```

## Development

```bash
# Install in editable mode
pip install -e .

# Run commands
wp-plugin --help
```
