#!/usr/bin/env bash
# ============================================================
# Start 100-region RL training (no Godot required)
#
# Launches:
#   1. Python DQN server (configurable state/action sizes)
#   2. JaCaMo with alice_100 agent
#
# Usage:
#   ./start_training_100.sh          # 100-room map
# ============================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON_DIR="$PROJECT_ROOT/mind/python"
MIND_DIR="$PROJECT_ROOT/mind"
LOGS_DIR="$PROJECT_ROOT/logs"

# Set JAVA_HOME to use project's JDK 17
export JAVA_HOME="$MIND_DIR/jdk-17.0.13+11"
export PATH="$JAVA_HOME/bin:$PATH"

mkdir -p "$LOGS_DIR"

# --- 100-region Configuration ---
echo "=== 100-region mode (extended map) ==="
export STATE_SIZE=200
export ACTION_SIZE=100
export HIDDEN_SIZE=256       # Larger hidden layer for 100 actions
export BUFFER_SIZE=500000   # 500K replay buffer for more experience
export EPSILON_DECAY=0.999985 # Very slow decay: stays exploratory longer
export TARGET_UPDATE=500     # Less frequent Q-target syncs for larger network

export MAX_EPISODES=500000
export MAX_STEPS=250

export PORT="${PORT:-5000}"
export GRADLE_OPTS="${GRADLE_OPTS:--Xmx256m}"

# --- Cleanup on exit ---
cleanup() {
    echo ""
    echo "Shutting down..."
    if [[ -n "${PYTHON_PID:-}" ]]; then
        kill "$PYTHON_PID" 2>/dev/null || true
        wait "$PYTHON_PID" 2>/dev/null || true
        echo "Python DQN server stopped."
    fi
}
trap cleanup EXIT INT TERM

# --- Start Python DQN server ---
echo "Starting Python DQN server (state=$STATE_SIZE, actions=$ACTION_SIZE, hidden=$HIDDEN_SIZE)..."
cd "$PYTHON_DIR"
python dqn_server.py > "$LOGS_DIR/dqn_server_100.log" 2>&1 &
PYTHON_PID=$!
cd "$PROJECT_ROOT"

# Wait for server to be ready
echo "Waiting for DQN server on port $PORT..."
for i in $(seq 1 30); do
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        echo "DQN server ready."
        break
    fi
    if ! kill -0 "$PYTHON_PID" 2>/dev/null; then
        echo "ERROR: DQN server failed to start. Check $LOGS_DIR/dqn_server_100.log"
        exit 1
    fi
    sleep 1
done

# --- Start JaCaMo agent ---
echo "Starting JaCaMo 100-region RL training..."
cd "$MIND_DIR"
./gradlew run100
