#!/usr/bin/env bash
# ============================================================
# Start graph-based RL training (no Godot required)
#
# Launches:
#   1. Python DQN server (configurable state/action sizes)
#   2. JaCaMo with alice_navigation_rl agent
#
# Usage:
#   ./start_navigation_training.sh          # 50-room map (default)
#   ./start_navigation_training.sh --small  # 11-room map (original)
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

# --- Configuration (50-room defaults, override with --small) ---
if [[ "${1:-}" == "--small" ]]; then
    echo "=== 11-room mode (original map) ==="
    export STATE_SIZE=22
    export ACTION_SIZE=11
    export HIDDEN_SIZE=64
    export BUFFER_SIZE=10000
    export EPSILON_DECAY=0.9999
    export TARGET_UPDATE=10
else
    echo "=== 50-room mode (extended map) ==="
    export STATE_SIZE=100
    export ACTION_SIZE=50
    export HIDDEN_SIZE=128       # Balanced size for memory-constrained machines
    export BUFFER_SIZE=100000    # 2x original but memory-safe
    export EPSILON_DECAY=0.99997 # Very slow decay: stays exploratory until ~70K eps
    export TARGET_UPDATE=200     # More frequent Q-target syncs
fi

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
python dqn_server.py > "$LOGS_DIR/dqn_server.log" 2>&1 &
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
        echo "ERROR: DQN server failed to start. Check $LOGS_DIR/dqn_server.log"
        exit 1
    fi
    sleep 1
done

# --- Start JaCaMo agent ---
echo "Starting JaCaMo navigation RL training..."
cd "$MIND_DIR"
./gradlew runNavigationRL
