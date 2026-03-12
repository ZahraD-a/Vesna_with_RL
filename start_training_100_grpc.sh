#!/usr/bin/env bash
# ============================================================
# Start 100-region RL training via gRPC (multi-threaded)
#
# Launches:
#   1. Python gRPC server with shared DQNAgent
#   2. JaCaMo with 8 parallel agents using gRPC
#
# Usage:
#   ./start_training_100_grpc.sh          # 8 parallel agents (default)
#   NUM_AGENTS=4 ./start_training_100_grpc.sh  # 4 agents
# ============================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON_DIR="$PROJECT_ROOT/mind/python"
MIND_DIR="$PROJECT_ROOT/mind"
LOGS_DIR="$PROJECT_ROOT/logs"

# --- Dynamic JAVA_HOME detection ---
if [ -d "$MIND_DIR/jdk-17.0.13+11" ]; then
    export JAVA_HOME="$MIND_DIR/jdk-17.0.13+11"
elif [ -d "/usr/lib/jvm/java-17-openjdk-amd64" ]; then
    export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
elif [ -d "/usr/lib/jvm/openjdk-17" ]; then
    export JAVA_HOME="/usr/lib/jvm/openjdk-17"
elif [ -n "${JAVA_HOME:-}" ] && [ -d "$JAVA_HOME" ]; then
    : # Use existing JAVA_HOME
else
    echo "ERROR: JDK 17 not found!"
    echo "Install with: sudo apt install openjdk-17-jdk"
    exit 1
fi
export PATH="$JAVA_HOME/bin:$PATH"

mkdir -p "$LOGS_DIR"

# --- 100-region gRPC Configuration (Optimized for RTX 4090 + 8 parallel agents) ---
export NUM_AGENTS="${NUM_AGENTS:-8}"
echo "=== 100-region gRPC mode | ${NUM_AGENTS} parallel agents | RTX 4090 optimized ==="
export STATE_SIZE=206       # 103 regions * 2 (current + goal)
export ACTION_SIZE=103      # 103 possible actions
export HIDDEN_SIZE=512      # Large network — RTX 4090 handles it
export BUFFER_SIZE=200000   # 200K shared replay buffer
export BATCH_SIZE=512       # Large batches for GPU utilization
export EPSILON_DECAY=0.99995  # Fast decay — 8 agents explore faster together
export TARGET_UPDATE=200     # Target sync every 200 global episodes
export TRAIN_STEPS_PER_ACTION=8  # 8 gradient steps per signal — background thread

export MAX_EPISODES=100000   # Per-agent episode cap
export MAX_STEPS=200        # Tighter episodes

# gRPC configuration
export GRPC_PORT="${GRPC_PORT:-50051}"
export PORT="${PORT:-5000}"  # HTTP port (fallback)
export GRADLE_OPTS="${GRADLE_OPTS:--Xmx256m}"

# Use gRPC by default
export USE_GRPC="${USE_GRPC:-true}"

# --- Cleanup on exit ---
cleanup() {
    echo ""
    echo "Shutting down..."
    if [[ -n "${PYTHON_PID:-}" ]]; then
        kill "$PYTHON_PID" 2>/dev/null || true
        wait "$PYTHON_PID" 2>/dev/null || true
        echo "Python gRPC server stopped."
    fi
}
trap cleanup EXIT INT TERM

# --- Kill any stale gRPC server processes holding port 50051 ---
STALE_PIDS=$(lsof -ti tcp:"$GRPC_PORT" 2>/dev/null || true)
if [[ -n "$STALE_PIDS" ]]; then
    echo "Killing stale processes on port $GRPC_PORT: $STALE_PIDS"
    echo "$STALE_PIDS" | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# --- Start Python gRPC server ---
cd "$PYTHON_DIR"

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PYTHON_EXE="$PYTHON_DIR/.venv/Scripts/python.exe"
else
    PYTHON_EXE="$PYTHON_DIR/.venv/bin/python"
fi

if [[ ! -f "$PYTHON_EXE" ]]; then
    echo "Warning: Virtual environment not found, using system python"
    PYTHON_EXE="python"
fi

echo "Using Python: $PYTHON_EXE"

# Start gRPC server (imports dqn_agent_grpc)
"$PYTHON_EXE" dqn_server_grpc.py > "$LOGS_DIR/dqn_server_100_grpc.log" 2>&1 &
PYTHON_PID=$!
cd "$PROJECT_ROOT"

# Wait for gRPC server
echo "Waiting for gRPC server on port $GRPC_PORT..."
for i in $(seq 1 30); do
    if netstat -tlnp 2>/dev/null | grep -q ":$GRPC_PORT " || ss -tlnp 2>/dev/null | grep -q ":$GRPC_PORT "; then
        echo "gRPC server ready."
        break
    fi
    if ! kill -0 "$PYTHON_PID" 2>/dev/null; then
        echo "ERROR: gRPC server failed to start. Check $LOGS_DIR/dqn_server_100_grpc.log"
        cat "$LOGS_DIR/dqn_server_100_grpc.log"
        exit 1
    fi
    sleep 1
done

# --- Start JaCaMo with parallel agents via gRPC ---
echo "Starting JaCaMo 100-region RL training via gRPC (${NUM_AGENTS} parallel agents)..."
cd "$MIND_DIR"
./gradlew run100_grpc
