#!/usr/bin/env bash
# ============================================================
# Start graph-based RL navigation training (no Godot required)
#
# Checkpoint produced:
#   --small  (11 regions)  -> checkpoints/alice11.pt             [default]
#   --medium (50 regions)  -> checkpoints/alice50.pt
#   --large  (103 regions) -> checkpoints/alice103.pt
#
# TensorBoard logs:
#   runs/alice11/
#   runs/alice50/
#   runs/alice103/
#
# Log files:
#   logs/dqn_server_11.log
#   logs/dqn_server_50.log
#   logs/dqn_server_103.log
#
# Usage:
#   ./start_navigation_training.sh            # 11 regions (default)
#   ./start_navigation_training.sh --small    # 11 regions
#   ./start_navigation_training.sh --medium   # 50 regions
#   ./start_navigation_training.sh --large    # 103 regions
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

# --- Parse size argument ---
SIZE="${1:---small}"

case "$SIZE" in
    --small)
        echo "=== 11-region mode ==="
        export STATE_SIZE=22
        export ACTION_SIZE=11
        export HIDDEN_SIZE=64
        export BUFFER_SIZE=10000
        export BATCH_SIZE=64
        export EPSILON_DECAY=0.9999
        export TARGET_UPDATE=10
        export MAX_EPISODES=100000
        export MAX_STEPS=100
        LOG_SUFFIX="11"
        GRADLE_TASK="runNavigationRL11"
        ;;
    --medium)
        echo "=== 50-region mode ==="
        export STATE_SIZE=100
        export ACTION_SIZE=50
        export HIDDEN_SIZE=128
        export BUFFER_SIZE=100000
        export BATCH_SIZE=128
        export EPSILON_DECAY=0.99997
        export TARGET_UPDATE=200
        export MAX_EPISODES=100000
        export MAX_STEPS=150
        LOG_SUFFIX="50"
        GRADLE_TASK="runNavigationRL50"
        ;;
    --large)
        echo "=== 103-region mode ==="
        export STATE_SIZE=206
        export ACTION_SIZE=103
        export HIDDEN_SIZE=128
        export BUFFER_SIZE=50000
        export BATCH_SIZE=128
        export EPSILON_DECAY=0.999985
        export TARGET_UPDATE=500
        export MAX_EPISODES=100000
        export MAX_STEPS=300
        LOG_SUFFIX="103"
        GRADLE_TASK="runNavigationRL103"
        ;;
    *)
        echo "Usage: $0 [--small|--medium|--large]"
        echo "  --small   11 regions  -> alice11.pt             (default)"
        echo "  --medium  50 regions  -> alice50.pt"
        echo "  --large   103 regions -> alice103.pt"
        exit 1
        ;;
esac

export PORT="${PORT:-5000}"
export GRADLE_OPTS="${GRADLE_OPTS:--Xmx256m}"

# --- Cleanup on exit ---
cleanup() {
    echo ""
    echo "Shutting down..."
    if [[ -n "${PYTHON_PID:-}" ]]; then
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            taskkill //F //PID "$PYTHON_PID" 2>/dev/null || true
        else
            kill "$PYTHON_PID" 2>/dev/null || true
            wait "$PYTHON_PID" 2>/dev/null || true
        fi
        echo "Python DQN server stopped."
    fi
}
trap cleanup EXIT INT TERM

# --- Kill stale server on port ---
kill_stale_on_port() {
    local port=$1
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        local pids=$(netstat -ano 2>/dev/null | grep ":$port .*LISTENING" | awk '{print $NF}' | sort -u)
        if [[ -n "$pids" ]]; then
            echo "Killing stale processes on port $port: $pids"
            for pid in $pids; do
                if [[ -n "$pid" && "$pid" =~ ^[0-9]+$ ]]; then
                    taskkill //F //PID "$pid" 2>/dev/null || true
                fi
            done
            sleep 3
        fi
    else
        local pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
        if [[ -n "$pids" ]]; then
            echo "Killing stale processes on port $port: $pids"
            echo "$pids" | xargs kill -9 2>/dev/null || true
            sleep 1
        fi
    fi
}
kill_stale_on_port "$PORT"

# --- Start Python DQN server ---
echo "Starting Python DQN server (state=$STATE_SIZE, actions=$ACTION_SIZE, hidden=$HIDDEN_SIZE)..."
echo "Checkpoint: checkpoints/alice${LOG_SUFFIX}.pt"
echo "Log: $LOGS_DIR/dqn_server_${LOG_SUFFIX}.log"
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
"$PYTHON_EXE" dqn_server.py > "$LOGS_DIR/dqn_server_${LOG_SUFFIX}.log" 2>&1 &
PYTHON_PID=$!
cd "$PROJECT_ROOT"

# Wait for server to be ready
echo "Waiting for DQN server on port $PORT..."
for i in $(seq 1 30); do
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        echo "DQN server ready."
        break
    fi
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        if ! ps -p "$PYTHON_PID" >/dev/null 2>&1; then
            echo "ERROR: DQN server failed to start. Check $LOGS_DIR/dqn_server_${LOG_SUFFIX}.log"
            exit 1
        fi
    else
        if ! kill -0 "$PYTHON_PID" 2>/dev/null; then
            echo "ERROR: DQN server failed to start. Check $LOGS_DIR/dqn_server_${LOG_SUFFIX}.log"
            exit 1
        fi
    fi
    sleep 1
done

# --- Start JaCaMo agent ---
echo "Starting JaCaMo navigation RL training (${LOG_SUFFIX} regions)..."
cd "$MIND_DIR"
./gradlew "$GRADLE_TASK"
