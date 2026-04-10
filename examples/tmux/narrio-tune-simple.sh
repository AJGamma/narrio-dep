#!/usr/bin/env bash
# Simple tmux script for Narrio multi-variant tuning
#
# This is a standalone script example showing how the narrio tune command
# uses tmux under the hood. You can customize this for your own workflows.
#
# Usage:
#   ./narrio-tune-simple.sh <input-file> <style1,style2,style3>
#
# Example:
#   ./narrio-tune-simple.sh article.md "OpenAI,Anthropic,Google"

set -e

# Handle nested tmux sessions
# If running inside tmux, unset TMUX to allow creating independent session
if [ -n "$TMUX" ]; then
    echo "Note: Running inside tmux. Creating independent session..."
    export TMUX=""
fi

# Configuration
INPUT_FILE="${1:-example.md}"
STYLES="${2:-OpenAI,Anthropic}"
SESSION_NAME="narrio-tune-$(date +%Y%m%d-%H%M%S)"

# Parse styles
IFS=',' read -ra STYLE_ARRAY <<< "$STYLES"
NUM_STYLES=${#STYLE_ARRAY[@]}

echo "Creating tmux session: $SESSION_NAME"
echo "Input file: $INPUT_FILE"
echo "Styles: ${STYLE_ARRAY[*]}"
echo ""

# Create new detached session with first window
tmux new-session -d -s "$SESSION_NAME" -n "variants"

# Give tmux a moment to initialize (helps prevent timing issues)
sleep 0.1

# Create pane layout based on number of styles
if [ "$NUM_STYLES" -eq 2 ]; then
    # Vertical split for 2 styles
    tmux split-window -h -t "$SESSION_NAME"
elif [ "$NUM_STYLES" -eq 3 ]; then
    # One left, two stacked right
    tmux split-window -h -t "$SESSION_NAME"
    tmux split-window -v -t "$SESSION_NAME"
elif [ "$NUM_STYLES" -eq 4 ]; then
    # 2x2 grid
    tmux split-window -h -t "$SESSION_NAME"
    tmux split-window -v -t "$SESSION_NAME"
    tmux select-pane -t 0
    tmux split-window -v -t "$SESSION_NAME"
else
    # For 5+ styles, create a flexible grid
    COLS=$(( (NUM_STYLES + 1) / 2 ))
    if [ "$COLS" -gt 3 ]; then
        COLS=3
    fi

    # Create columns
    for ((i=1; i<COLS; i++)); do
        tmux split-window -h -t "$SESSION_NAME"
    done

    # Split each column vertically as needed
    for ((col=0; col<COLS; col++)); do
        PANES_IN_COL=$(( (NUM_STYLES + COLS - 1 - col) / COLS ))
        if [ "$PANES_IN_COL" -gt 1 ]; then
            tmux select-pane -t "$col"
            for ((j=1; j<PANES_IN_COL; j++)); do
                tmux split-window -v -t "$SESSION_NAME"
            done
        fi
    done
fi

# Balance panes for equal sizing
if [ "$NUM_STYLES" -gt 1 ]; then
    tmux select-layout -t "$SESSION_NAME" tiled
fi

# Execute variants in panes
for i in "${!STYLE_ARRAY[@]}"; do
    STYLE="${STYLE_ARRAY[$i]}"
    COMMAND="narrio run --content-type article --markdown \"$INPUT_FILE\" --style $STYLE"

    echo "Pane $i: Running $STYLE"
    tmux send-keys -t "$SESSION_NAME.$i" "$COMMAND" Enter
done

# Create summary window
tmux new-window -t "$SESSION_NAME" -n "summary"

# Write summary
tmux send-keys -t "$SESSION_NAME" "clear" Enter
tmux send-keys -t "$SESSION_NAME" "echo '=== Narrio Multi-Variant Tuning Pipeline ==='" Enter
tmux send-keys -t "$SESSION_NAME" "echo 'Session: $SESSION_NAME'" Enter
tmux send-keys -t "$SESSION_NAME" "echo 'Input: $INPUT_FILE'" Enter
tmux send-keys -t "$SESSION_NAME" "echo 'Variants: $NUM_STYLES'" Enter
tmux send-keys -t "$SESSION_NAME" "echo ''" Enter
tmux send-keys -t "$SESSION_NAME" "echo 'Variants running:'" Enter

for i in "${!STYLE_ARRAY[@]}"; do
    STYLE="${STYLE_ARRAY[$i]}"
    tmux send-keys -t "$SESSION_NAME" "echo '  [$i] $STYLE: running in pane $i'" Enter
done

tmux send-keys -t "$SESSION_NAME" "echo ''" Enter
tmux send-keys -t "$SESSION_NAME" "echo 'Navigation:'" Enter
tmux send-keys -t "$SESSION_NAME" "echo '  - Ctrl+b, 0: Switch to variants window'" Enter
tmux send-keys -t "$SESSION_NAME" "echo '  - Ctrl+b, 1: Switch back to this summary'" Enter
tmux send-keys -t "$SESSION_NAME" "echo '  - Ctrl+b, d: Detach from session'" Enter

# Select summary window (window 1)
tmux select-window -t 1

# Attach to session
echo "Attaching to session '$SESSION_NAME'..."
echo "Use 'Ctrl+b d' to detach from the session."
echo ""

tmux attach-session -t "$SESSION_NAME"
