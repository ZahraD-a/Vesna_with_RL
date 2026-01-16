#!/bin/bash
# Stop all processes (JaCaMo, Godot, Python RL Service)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping all Vesna processes...${NC}"

# Kill Gradle processes
GRADLE_PIDS=$(pgrep -f "gradlew.*run")
if [ ! -z "$GRADLE_PIDS" ]; then
    echo -e "  ${RED}[KILL]${NC} Killing Gradle processes: $GRADLE_PIDS"
    pkill -9 -f "gradlew.*run"
else
    echo -e "  ${GREEN}[OK]${NC} No Gradle processes running"
fi

# Kill JaCaMo processes
JACAMO_PIDS=$(pgrep -f "jacamo")
if [ ! -z "$JACAMO_PIDS" ]; then
    echo -e "  ${RED}[KILL]${NC} Killing JaCaMo processes: $JACAMO_PIDS"
    pkill -9 -f "jacamo"
else
    echo -e "  ${GREEN}[OK]${NC} No JaCaMo processes running"
fi

# Kill Python RL Service
PYTHON_PIDS=$(pgrep -f "dqn_server.py")
if [ ! -z "$PYTHON_PIDS" ]; then
    echo -e "  ${RED}[KILL]${NC} Killing Python RL service: $PYTHON_PIDS"
    pkill -9 -f "dqn_server.py"
else
    echo -e "  ${GREEN}[OK]${NC} No Python RL service running"
fi

# Kill Godot
GODOT_PIDS=$(pgrep -f "Godot")
if [ ! -z "$GODOT_PIDS" ]; then
    echo -e "  ${RED}[KILL]${NC} Killing Godot processes: $GODOT_PIDS"
    pkill -9 -f "Godot"
else
    echo -e "  ${GREEN}[OK]${NC} No Godot processes running"
fi

echo -e "${GREEN}[OK] All processes stopped!${NC}"
