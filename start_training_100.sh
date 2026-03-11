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
export STATE_SIZE=206       # 103 regions * 2 (current + goal)
export ACTION_SIZE=103      # 103 possible actions
export HIDDEN_SIZE=128      # Reduced from 256 to save memory
export BUFFER_SIZE=50000    # 50K replay buffer (reduced to prevent MemoryError)
export BATCH_SIZE=128       # Increased for more stable gradients with GPU acceleration
export EPSILON_DECAY=0.999985 # Very slow decay: stays exploratory longer
export TARGET_UPDATE=500     # Less frequent Q-target syncs for larger network

export MAX_EPISODES=100000  # Reduced from 500K - sufficient for 100-region convergence
export MAX_STEPS=300        # Increased from 250 - allows more exploration in 100-region space

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

# Use virtual environment Python on Windows
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PYTHON_EXE="$PYTHON_DIR/.venv/Scripts/python.exe"
else
    PYTHON_EXE="$PYTHON_DIR/.venv/bin/python"
fi

# Fallback to system python if venv not found
if [[ ! -f "$PYTHON_EXE" ]]; then
    echo "Warning: Virtual environment not found, using system python"
    PYTHON_EXE="python"
fi

echo "Using Python: $PYTHON_EXE"
"$PYTHON_EXE" dqn_server.py > "$LOGS_DIR/dqn_server_100.log" 2>&1 &
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
