#!/bin/bash
# Start Godot and JaCaMo Together
# This script launches both processes and monitors them

set -e  # Exit on error

VESNA_ROOT="/home/hamid/Desktop/Projects/Vesna_RL"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Starting VEsNA BDI System${NC}"
echo -e "${GREEN}======================================${NC}"

# Step 1: Start Godot in background
echo -e "\n${YELLOW}[1/2] Starting Godot Environment...${NC}"

"$VESNA_ROOT/Godot_v4.5.1-stable_linux.x86_64" --path "$VESNA_ROOT/env/office" > /tmp/godot.log 2>&1 &
GODOT_PID=$!

echo -e "${GREEN}✓ Godot started (PID: $GODOT_PID)${NC}"
echo "  Log: /tmp/godot.log"

# Wait for Godot to initialize (3 seconds)
echo -e "${YELLOW}  Waiting for Godot to initialize...${NC}"
sleep 3
echo -e "${GREEN}  ✓ Godot should be ready!${NC}"

# Step 2: Start JaCaMo
echo -e "\n${YELLOW}[2/2] Starting JaCaMo (Jason + CArtAgO + Moise)...${NC}"
cd "$VESNA_ROOT"

export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# Run JaCaMo in foreground (so we can see logs)
echo -e "${GREEN}✓ Starting JaCaMo...${NC}"
echo -e "${YELLOW}  Press Ctrl+C to stop both Godot and JaCaMo${NC}"
echo ""

# Trap Ctrl+C to kill both processes
trap "echo -e '\n${YELLOW}Stopping processes...${NC}'; kill $GODOT_PID 2>/dev/null; echo -e '${GREEN}✓ All processes stopped${NC}'; exit 0" INT

# Run JaCaMo (this blocks until user presses Ctrl+C)
./gradlew -p mind run

# If gradlew exits normally (not via Ctrl+C), clean up Godot
kill $GODOT_PID 2>/dev/null
echo -e "${GREEN}✓ All processes stopped${NC}"
