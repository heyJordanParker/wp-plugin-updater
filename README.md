# WP Plugin Updater

Automate WordPress plugin and theme updates in GitHub Actions. Supports WordPress.org, WooCommerce Software Licensing API, and custom APIs.

## Quick Start

**Single plugin/theme? → [Single-Branch Workflow](#single-branch-workflow)**
**Free + Pro versions? → [Multi-Branch Workflow](#multi-branch-workflow)**

## Installation

```bash
pip install git+https://github.com/heyJordanParker/wp-plugin-updater.git
```

## Commands

### WordPress.org
```bash
wp-plugin check-wordpress-org woocommerce
wp-plugin download-wordpress woocommerce 8.5.2 plugin-free
```

### WooCommerce Software Licensing API
```bash
wp-plugin check-license \
  "https://example.com/?wc-api=upgrade-api&request=pluginupdatecheckall" \
  "license-key" \
  "plugin-pro/plugin-pro.php" \
  "Plugin Pro" \
  "user@example.com" \
  "https://example.com" \
  "instance-id"

wp-plugin download-licensed "https://s3.amazonaws.com/..." plugin-pro
```

**Getting instance ID:**
```bash
wp option get {vendor}_plugins_info --format=json
```
Find your plugin's SHA1 hash, copy its `instance` value.

### Merge
```bash
# Merge multiple branches (first=base, rest overlay)
wp-plugin merge plugin-free plugin-pro --no-push
```

## Workflow Templates

### Single-Branch Workflow

**Use when:** One plugin/theme from one source (premium-only, single licensed plugin)

**Setup:**
1. Create empty repo, clone it
2. Add `.gitignore`, `README.md`
3. Create `.github/workflows/update.yml` with template below
4. Commit and push (no plugin code yet)
5. Add GitHub secrets
6. Settings → Actions → General → Check "Allow GitHub Actions to create and approve pull requests"
7. Trigger workflow (Actions → Run workflow)

```yaml
name: Update Plugin

on:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  update:
    runs-on: ubuntu-latest
    env:
      PR_TITLE_PREFIX: "Auto-update: Plugin name"

    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Git
        run: |
          git config --global user.name "GitHub Actions"
          git config --global user.email "actions@github.com"

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y jq
          pip3 install git+https://github.com/heyJordanParker/wp-plugin-updater.git

      # CUSTOMIZE THIS SECTION for your API
      - name: Check for updates
        id: check
        env:
          LICENSE_KEY: ${{ secrets.LICENSE_KEY }}
        run: |
          # Example: Custom API
          INFO=$(curl -s "https://api.example.com/check?key=$LICENSE_KEY&version=1.0.0")
          VERSION=$(echo "$INFO" | jq -r '.new_version')
          DOWNLOAD=$(echo "$INFO" | jq -r '.package')

          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "download=$DOWNLOAD" >> $GITHUB_OUTPUT

      - name: Download plugin
        if: steps.check.outputs.version
        run: wp-plugin download-licensed "${{ steps.check.outputs.download }}" plugin-premium

      # Copy to master (SINGLE BRANCH = git checkout)
      - name: Checkout master
        if: steps.check.outputs.version
        run: git checkout master && git reset --hard origin/master

      - name: Copy files
        if: steps.check.outputs.version
        run: git checkout plugin-premium -- .

      - name: Close old PRs
        if: steps.check.outputs.version
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh pr list --base master --state open --json number,title --jq ".[] | select(.title | startswith(\"${{ env.PR_TITLE_PREFIX }}\")) | .number" | while read pr; do
            gh pr close $pr --comment "Superseded by newer update" --delete-branch
          done || true

      - name: Create PR
        if: steps.check.outputs.version
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          branch: auto-update-${{ github.run_number }}
          base: master
          title: "${{ env.PR_TITLE_PREFIX }}"
          body: "**Version**: ${{ steps.check.outputs.version }}"
          commit-message: "Update to v${{ steps.check.outputs.version }}"
```

### Multi-Branch Workflow

**Use when:** Free + Pro versions, or multiple plugins to merge

**Setup:** Same as single-branch, then:

```yaml
name: Update Plugins

on:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  update:
    runs-on: ubuntu-latest
    env:
      PR_TITLE_PREFIX: "Auto-update: Plugins"

    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Git
        run: |
          git config --global user.name "GitHub Actions"
          git config --global user.email "actions@github.com"

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y jq
          pip3 install git+https://github.com/heyJordanParker/wp-plugin-updater.git

      - name: Check for updates
        id: check
        env:
          LICENSE_KEY: ${{ secrets.LICENSE_KEY }}
          LICENSE_EMAIL: ${{ secrets.LICENSE_EMAIL }}
          LICENSE_DOMAIN: ${{ secrets.LICENSE_DOMAIN }}
          INSTANCE_ID: ${{ secrets.INSTANCE_ID }}
        run: |
          # Free plugin
          FREE=$(wp-plugin check-wordpress-org plugin-slug)
          echo "free=$(echo "$FREE" | jq -r '.version')" >> $GITHUB_OUTPUT

          # Pro plugin
          PRO=$(wp-plugin check-license \
            "https://example.com/?wc-api=upgrade-api&request=pluginupdatecheckall" \
            "$LICENSE_KEY" "plugin-pro/plugin-pro.php" "Plugin Pro" \
            "$LICENSE_EMAIL" "$LICENSE_DOMAIN" "$INSTANCE_ID")

          echo "pro=$(echo "$PRO" | jq -r '.version')" >> $GITHUB_OUTPUT
          echo "pro_url=$(echo "$PRO" | jq -r '.download_url')" >> $GITHUB_OUTPUT

      - name: Download free
        if: steps.check.outputs.free
        run: wp-plugin download-wordpress plugin-slug ${{ steps.check.outputs.free }} plugin-free

      - name: Download pro
        if: steps.check.outputs.pro
        run: wp-plugin download-licensed "${{ steps.check.outputs.pro_url }}" plugin-pro

      # Merge to master (MULTI-BRANCH = wp-plugin merge)
      - name: Checkout master
        if: steps.check.outputs.free || steps.check.outputs.pro
        run: git checkout master && git reset --hard origin/master

      - name: Merge branches
        if: steps.check.outputs.free || steps.check.outputs.pro
        run: wp-plugin merge plugin-free plugin-pro --no-push

      - name: Close old PRs
        if: steps.check.outputs.free || steps.check.outputs.pro
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh pr list --base master --state open --json number,title --jq ".[] | select(.title | startswith(\"${{ env.PR_TITLE_PREFIX }}\")) | .number" | while read pr; do
            gh pr close $pr --comment "Superseded by newer update" --delete-branch
          done || true

      - name: Create PR
        if: steps.check.outputs.free || steps.check.outputs.pro
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          branch: auto-update-${{ github.run_number }}
          base: master
          title: "${{ env.PR_TITLE_PREFIX }}"
          body: |
            **Free**: ${{ steps.check.outputs.free }}
            **Pro**: ${{ steps.check.outputs.pro }}
          commit-message: "Update Free v${{ steps.check.outputs.free }} and Pro v${{ steps.check.outputs.pro }}"
```

## API Integration

### WordPress.org

```yaml
INFO=$(wp-plugin check-wordpress-org plugin-slug)
VERSION=$(echo "$INFO" | jq -r '.version')
```

Then: `wp-plugin download-wordpress plugin-slug $VERSION plugin-free`

**Secrets:** None

### WooCommerce Software Licensing

```yaml
INFO=$(wp-plugin check-license \
  "https://example.com/?wc-api=upgrade-api&request=pluginupdatecheckall" \
  "$LICENSE_KEY" "plugin-pro/plugin-pro.php" "Plugin Pro" \
  "$LICENSE_EMAIL" "$LICENSE_DOMAIN" "$INSTANCE_ID")

VERSION=$(echo "$INFO" | jq -r '.version')
DOWNLOAD=$(echo "$INFO" | jq -r '.download_url')
```

Then: `wp-plugin download-licensed "$DOWNLOAD" plugin-pro`

**Secrets:** `LICENSE_KEY`, `LICENSE_EMAIL`, `LICENSE_DOMAIN`, `INSTANCE_ID`

### Custom API (curl)

```yaml
INFO=$(curl -s "https://api.example.com/check?key=$LICENSE_KEY&version=1.0.0")
VERSION=$(echo "$INFO" | jq -r '.new_version')
DOWNLOAD=$(echo "$INFO" | jq -r '.package')
```

Then: `wp-plugin download-licensed "$DOWNLOAD" plugin-branch`

**Secrets:** Varies by API

## Key Concepts

### Branch Strategy

- **master** - Current version, has `.github/` workflows
- **Storage branches** (`plugin-free`, `plugin-pro`) - Permanent, store versions from sources
- **PR branches** (`auto-update-123`) - Temporary, created by peter-evans action

### Locked Paths

Files preserved during downloads: `.git`, `.github`, `.gitignore`

**Why?** Without this, downloading a plugin deletes your workflows.

**How it works:**
1. Storage branch syncs `.github/` from master before download
2. Download preserves `.github/` during cleanup
3. Copy/merge preserves `.github/`

**Add custom locked paths:**
```yaml
- name: Download
  env:
    LOCKED_PATHS: "scripts,docs"
  run: wp-plugin download-licensed "$URL" plugin-branch
```

### Update Flow

1. Download to storage branch (syncs `.github/` from master first)
2. Checkout master + reset
3. Copy (single) or merge (multi) to master working dir
4. Close old PRs
5. peter-evans creates temp PR branch and commits

## Troubleshooting

### `Error: Need at least 2 branches to merge`

Using `wp-plugin merge` with single branch.

**Fix:** Use `git checkout branch -- .` for single-branch workflows.

### Infrastructure files deleted

Storage branches missing `.github/` after workflow runs.

**Fix:** Update wp-plugin-updater: `pip3 install --upgrade git+https://github.com/heyJordanParker/wp-plugin-updater.git`

### `Error: GitHub Actions is not permitted to create or approve pull requests`

GitHub Actions can't create PRs by default.

**Fix:** Settings → Actions → General → Workflow permissions → Check "Allow GitHub Actions to create and approve pull requests"

### Old PRs not closing

`PR_TITLE_PREFIX` doesn't match PR titles.

**Fix:** Verify prefix exactly matches:
```yaml
env:
  PR_TITLE_PREFIX: "Auto-update: Plugin name"  # Must match PR title
```

### `Error: Resource not accessible by integration`

Missing workflow permissions.

**Fix:**
```yaml
permissions:
  contents: write
  pull-requests: write
```

## Examples

- Multi-branch (free + pro): `heyJordanParker/funnelkit`
- Single-branch (premium): `heyJordanParker/bricks`

## Development

```bash
git clone https://github.com/heyJordanParker/wp-plugin-updater.git
cd wp-plugin-updater
pip install -e .
wp-plugin --help
```

## License

MIT
