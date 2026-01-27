#!/bin/bash
# Start VEsNA RL System
# Order: Godot (environment) → Python RL Service → Jason (agent)

set -e  # Exit on error

VESNA_ROOT="$(cd "$(dirname "$0")" && pwd)"
LOGS_DIR="$VESNA_ROOT/logs"
mkdir -p "$LOGS_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}======================================${NC}"
echo -e "${CYAN}  VEsNA RL-as-Service System${NC}"
echo -e "${CYAN}======================================${NC}"

# Step 1: Start Godot
echo -e "\n${YELLOW}[1/3] Starting Godot Environment...${NC}"

"/c/Users/zahra/Desktop/softwares/Godot_v4.5.1-stable_win64.exe/Godot_v4.5.1-stable_win64.exe" --path "$VESNA_ROOT/env/office" > "$LOGS_DIR/godot.log" 2>&1 &
GODOT_PID=$!

echo -e "${GREEN}[OK] Godot started (PID: $GODOT_PID)${NC}"
echo "  Log: $LOGS_DIR/godot.log"
sleep 3

# Step 2: Start Python RL Service
echo -e "\n${YELLOW}[2/3] Starting Python RL Service...${NC}"

cd "$VESNA_ROOT/mind/python"
source .venv/Scripts/activate
python dqn_server.py > "$LOGS_DIR/rl_service.log" 2>&1 &
PYTHON_PID=$!

echo -e "${GREEN}[OK] RL Service starting (PID: $PYTHON_PID)${NC}"
echo "  Log: $LOGS_DIR/rl_service.log"

# Wait for RL service to be ready
echo -e "${YELLOW}  Waiting for RL service...${NC}"
for i in {1..10}; do
    if curl -s http://localhost:5000/health > /dev/null 2>&1; then
        echo -e "${GREEN}  [OK] RL Service ready!${NC}"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}  [FAIL] RL Service failed to start!${NC}"
        kill $GODOT_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# Step 3: Start JaCaMo (RL version)
echo -e "\n${YELLOW}[3/3] Starting JaCaMo (RL Training)...${NC}"
cd "$VESNA_ROOT"

export JAVA_HOME="$VESNA_ROOT/mind/jdk-17.0.13+11"
unset JASON_HOME
rm -rf ~/.jason 2>/dev/null

echo -e "${GREEN}[OK] Starting JaCaMo...${NC}"
echo -e "${YELLOW}  Press Ctrl+C to stop all processes${NC}"
echo ""
echo -e "${CYAN}======================================${NC}"
echo -e "${CYAN}  System Running - Watch the Training${NC}"
echo -e "${CYAN}======================================${NC}"
echo ""

# Trap Ctrl+C to kill all processes
cleanup() {
    echo -e "\n${YELLOW}Stopping all processes...${NC}"
    kill $PYTHON_PID 2>/dev/null && echo -e "  ${GREEN}[OK]${NC} Python stopped"
    kill $GODOT_PID 2>/dev/null && echo -e "  ${GREEN}[OK]${NC} Godot stopped"
    echo -e "${GREEN}[OK] All processes stopped${NC}"
    exit 0
}
trap cleanup INT TERM

# Run JaCaMo RL task (gradlew is in mind/)
cd "$VESNA_ROOT/mind"
./gradlew runRL

# Cleanup on normal exit
cleanup
