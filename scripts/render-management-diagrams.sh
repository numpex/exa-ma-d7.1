#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd "$(dirname "$0")/.." && pwd)
diagram_dir="$repo_dir/graphics/management"
mermaid_cli_version=12.0.0

if command -v mmdc >/dev/null && [[ $(mmdc --version) == "$mermaid_cli_version" ]]; then
    renderer=(mmdc)
else
    renderer=(npx --yes --package "@mermaid-js/mermaid-cli@$mermaid_cli_version" -- mmdc)
fi

chrome='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
if [[ -z ${PUPPETEER_EXECUTABLE_PATH:-} && -x "$chrome" ]]; then
    export PUPPETEER_EXECUTABLE_PATH="$chrome"
fi

render_dir=$(mktemp -d)
trap 'rm -rf "$render_dir"' EXIT

for source in "$diagram_dir"/*.mmd; do
    diagram=$(basename "$source" .mmd)
    "${renderer[@]}" --input "$source" \
        --configFile "$diagram_dir/mermaid-config.json" \
        --output "$render_dir/$diagram.pdf"
done

for pdf in "$render_dir"/*.pdf; do
    mv "$pdf" "$diagram_dir/"
done
