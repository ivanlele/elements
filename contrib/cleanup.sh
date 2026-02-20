#!/usr/bin/env bash
# Script to clean up test, bitcoin, and elements related files from /tmp/
# Works without sudo - only removes files/directories owned by current user

# Color output for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Cleaning up /tmp/ - removing items containing 'test', 'bitcoin', or 'elements'...${NC}"
echo ""

# Counter for deleted items
deleted_count=0
failed_count=0

# Build a combined find command to get all matching items at once
# Find items matching any of the patterns, owned by current user
echo -e "${YELLOW}Finding all matching items...${NC}"

# Use find with -o (or) to match any of the patterns in a single pass
# Process directories depth-first to avoid issues with nested items
mapfile -t items < <(find /tmp -user "$(whoami)" \( -iname "*test*" -o -iname "*bitcoin*" -o -iname "*elements*" \) -print 2>/dev/null | sort -r || true)

if [ ${#items[@]} -eq 0 ]; then
    echo -e "${YELLOW}No matching items found.${NC}"
    exit 0
fi

echo -e "${YELLOW}Found ${#items[@]} items to remove.${NC}"
echo ""

# Remove all items
for item in "${items[@]}"; do
    if [ -e "$item" ]; then
        # Try to remove the item
        if rm -rf "$item" 2>/dev/null; then
            echo -e "${GREEN}  Removed: $item${NC}"
            ((deleted_count++))
        else
            echo -e "${RED}  Failed to remove: $item${NC}"
            ((failed_count++))
        fi
    fi
done

echo ""
echo -e "${GREEN}Cleanup complete!${NC}"
echo -e "  Deleted: ${deleted_count} items"
if [ $failed_count -gt 0 ]; then
    echo -e "  Failed: ${RED}${failed_count}${NC} items"
fi
