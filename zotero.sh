#!/bin/bash

GROUP_ID="5582837"
API_KEY=${ZOTERO_API_KEY}

declare -A existing_collections
declare -A collection_keys

fetch_existing_collections() {
  local start=0
  local limit=100
  local total=1

  # Get total number of collections
  total=$(curl -s -I -X GET "https://api.zotero.org/groups/$GROUP_ID/collections" \
    -H "Zotero-API-Version: 3" \
    -H "Authorization: Bearer $API_KEY" | grep -i 'Total-Results' | awk '{print $2}' | tr -d '\r')

  while [[ $start -lt $total ]]; do
    response=$(curl -s -X GET "https://api.zotero.org/groups/$GROUP_ID/collections?limit=$limit&start=$start" \
      -H "Zotero-API-Version: 3" \
      -H "Authorization: Bearer $API_KEY")

    # Parse the response and store collections in an associative array
    while read -r collection; do
      key=$(echo "$collection" | jq -r '.key')
      name=$(echo "$collection" | jq -r '.data.name')
      parent=$(echo "$collection" | jq -r '.data.parentCollection')
      existing_collections["$name|$parent"]="$key"
      echo "Found collection '$name' in '$parent' with key $key."
    done < <(echo "$response" | jq -c '.[]')

    start=$((start + limit))
  done
}

fetch_existing_collections existing_collections
echo "Existing collections: ${!existing_collections[@]}"

# Create top-level collections
collections=("Our Publications" "External Publications")
top_level_keys=()

for collection in "${collections[@]}"; do
  # Check if collection exists
  parent="false"
  collection_key="${existing_collections["$collection|$parent"]}"
  echo "Collection key: $collection_key"

  if [[ -n "$collection_key" ]]; then
    echo "Collection '$collection' already exists with key $collection_key."
  else
    # Create collection
    response=$(curl -s -X POST "https://api.zotero.org/groups/$GROUP_ID/collections" \
      -H "Zotero-API-Version: 3" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $API_KEY" \
      -d "[{\"name\": \"$collection\"}]")

    echo "Response for creating '$collection': $response"

    # Extract the key
    collection_key=$(echo "$response" | jq -r '.success."0"')

    if [[ -z "$collection_key" || "$collection_key" == "null" ]]; then
      echo "Failed to create collection '$collection'. Exiting."
      exit 1
    fi

    # Update the existing collections array
    existing_collections["$collection|$parent"]="$collection_key"
    echo "Created collection '$collection' with key $collection_key."
  fi

  # Store the key for use in sub-collections
  collection_keys["$collection"]="$collection_key"
done
echo "Top-level collection keys: ${collection_keys[@]}"

# Create WP sub-collections under each top-level collection
wps=("WP1" "WP2" "WP3" "WP4" "WP5" "WP6" "WP7")
sub_collections=("Articles" "Software" "Technical Notes" "Deliverables")

for top_collection in "${collections[@]}"; do
  parent_key="${collection_keys["$top_collection"]}"

  for wp in "${wps[@]}"; do
    # Check if WP collection exists
    wp_key="${existing_collections["$wp|$parent_key"]}"

    if [[ -n "$wp_key" ]]; then
      echo "WP '$wp' under '$top_collection' already exists with key $wp_key."
    else
      # Create WP collection
      response=$(curl -s -X POST "https://api.zotero.org/groups/$GROUP_ID/collections" \
        -H "Zotero-API-Version: 3" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $API_KEY" \
        -d "[{\"name\": \"$wp\", \"parentCollection\": \"$parent_key\"}]")

      echo "Response for creating WP '$wp' under '$top_collection': $response"

      wp_key=$(echo "$response" | jq -r '.success."0"')

      if [[ -z "$wp_key" || "$wp_key" == "null" ]]; then
        echo "Failed to create WP '$wp' under '$top_collection'. Exiting."
        exit 1
      fi

      # Update existing collections
      existing_collections["$wp|$parent_key"]="$wp_key"
      echo "Created WP '$wp' under '$top_collection' with key $wp_key."
    fi

    # Create sub-collections under WP
    for sub_collection in "${sub_collections[@]}"; do
      sub_key="${existing_collections["$sub_collection|$wp_key"]}"

      if [[ -n "$sub_key" ]]; then
        echo "Sub-collection '$sub_collection' under '$wp' already exists with key $sub_key."
      else
        # Create sub-collection
        response=$(curl -s -X POST "https://api.zotero.org/groups/$GROUP_ID/collections" \
          -H "Zotero-API-Version: 3" \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $API_KEY" \
          -d "[{\"name\": \"$sub_collection\", \"parentCollection\": \"$wp_key\"}]")

        echo "Response for creating '$sub_collection' under '$wp': $response"

        sub_key=$(echo "$response" | jq -r '.success."0"')

        if [[ -z "$sub_key" || "$sub_key" == "null" ]]; then
          echo "Failed to create sub-collection '$sub_collection' under '$wp'. Exiting."
          exit 1
        fi

        # Update existing collections
        existing_collections["$sub_collection|$wp_key"]="$sub_key"
        echo "Created sub-collection '$sub_collection' under '$wp' with key $sub_key."
      fi
    done
  done
done