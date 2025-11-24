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
wp-plugin check-license <api_url> <license_key> <product_id> <email>
# Returns: {"version": "3.13.3", "download_url": "https://..."}
```

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
