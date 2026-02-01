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

# Verify Python virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}======================================${NC}"
    echo -e "${RED}  ERROR: Python virtual environment not found!${NC}"
    echo -e "${RED}======================================${NC}"
    echo ""
    echo -e "${YELLOW}Expected location:${NC}"
    echo "  $VESNA_ROOT/mind/python/.venv"
    echo ""
    echo -e "${YELLOW}The virtual environment has not been created yet.${NC}"
    echo ""
    echo -e "${CYAN}To fix this, run the following commands:${NC}"
    echo ""
    echo "  1. Navigate to the Python directory:"
    echo -e "     ${GREEN}cd $VESNA_ROOT/mind/python${NC}"
    echo ""
    echo "  2. Create the virtual environment:"
    echo -e "     ${GREEN}python -m venv .venv${NC}"
    echo ""
    echo "  3. Activate the virtual environment:"
    echo -e "     ${GREEN}source .venv/Scripts/activate${NC}"
    echo ""
    echo "  4. Install the required packages:"
    echo -e "     ${GREEN}pip install -r requirements.txt${NC}"
    echo ""
    echo "  5. Then run this script again:"
    echo -e "     ${GREEN}./start_all.sh${NC}"
    echo ""
    kill $GODOT_PID 2>/dev/null
    exit 1
fi

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

unset JASON_HOME
export JAVA_HOME="$VESNA_ROOT/mind/jdk-17.0.13+11"
rm -rf ~/.jason 2>/dev/null

# Verify JAVA_HOME is valid
if [ ! -d "$JAVA_HOME" ]; then
    echo -e "${RED}======================================${NC}"
    echo -e "${RED}  ERROR: JDK not found!${NC}"
    echo -e "${RED}======================================${NC}"
    echo ""
    echo -e "${YELLOW}JAVA_HOME is set to:${NC}"
    echo "  $JAVA_HOME"
    echo ""
    echo -e "${YELLOW}But this directory does not exist.${NC}"
    echo ""
    echo -e "${CYAN}To fix this, do ONE of the following:${NC}"
    echo ""
    echo "  1. Copy JDK 17 from another Vesna project:"
    echo "     cp -r /path/to/Vesna_RL/mind/jdk-17.0.13+11 $VESNA_ROOT/mind/"
    echo ""
    echo "  2. Download Adoptium JDK 17.0.13+11:"
    echo "     https://adoptium.net/temurin/releases/?version=17"
    echo "     Extract to: $VESNA_ROOT/mind/jdk-17.0.13+11"
    echo ""
    echo "  3. Use your system JDK 17+ (temporary fix):"
    echo "     export JAVA_HOME=/path/to/your/jdk-17"
    echo ""
    kill $PYTHON_PID 2>/dev/null
    kill $GODOT_PID 2>/dev/null
    exit 1
fi

echo -e "${GREEN}[OK] JAVA_HOME set to: $JAVA_HOME${NC}"

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
