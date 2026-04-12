#!/bin/bash
# Launch TensorBoard for VEsNA RL Training Visualization
#
# This script starts TensorBoard to visualize training metrics in your browser
# Logs are located at: runs/alice_navigation_rl_100/

echo "Starting TensorBoard..."
echo "Log directory: runs/alice_navigation_rl_100/"
echo ""
echo "TensorBoard will be available at: http://localhost:6006"
echo "Press Ctrl+C to stop TensorBoard"
echo ""

# Activate virtual environment and launch TensorBoard
cd "$(dirname "$0")"
source mind/python/.venv/Scripts/activate 2>/dev/null || source mind/python/.venv/bin/activate

tensorboard --logdir=runs/alice_navigation_rl_100 --port=6006 --bind_all
