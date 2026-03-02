#!/usr/bin/env bash
# ============================================================
# Run a BDI mission using Alice's trained RL navigation policy.
#
# This demonstrates the hybrid BDI-RL architecture:
#   - Jason (BDI) plans the mission (pickup, deliver, patrol)
#   - Python (DQN) provides the navigation skill (trained checkpoint)
#   - NO retraining! Uses checkpoints/alice.pt as-is.
#
# Usage:
#   ./start_mission.sh              # run delivery mission (default)
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

# 50-room config (must match the trained checkpoint)
export STATE_SIZE=100
export ACTION_SIZE=50
export HIDDEN_SIZE=128
export BUFFER_SIZE=10000       # small buffer OK — no training happening
export EPSILON_DECAY=0.99997
export TARGET_UPDATE=200
export PORT="${PORT:-5000}"
export GRADLE_OPTS="${GRADLE_OPTS:--Xmx256m}"

# --- Check checkpoint exists ---
if [[ ! -f "$PROJECT_ROOT/checkpoints/alice.pt" ]]; then
    echo "ERROR: No trained checkpoint found at checkpoints/alice.pt"
    echo "Train first with: ./start_navigation_training.sh"
    exit 1
fi

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
echo "Starting Python DQN server (eval mode — no training)..."
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

# --- Run the mission ---
echo ""
echo "=============================================="
echo "  Running BDI Mission (trained RL policy)"
echo "=============================================="
echo ""
cd "$MIND_DIR"
./gradlew runMission
