#!/usr/bin/env bash
# Tmuxifier layout for Narrio multi-variant tuning
#
# This is an example tmuxifier layout that can be used as a template
# for custom narrio tune sessions.
#
# Usage:
#   1. Install tmuxifier: https://github.com/jimeh/tmuxifier
#   2. Copy this file to your tmuxifier layouts directory:
#      cp narrio-tune.tmuxifier.sh ~/.tmuxifier/layouts/narrio-tune.window.sh
#   3. Load the layout:
#      tmuxifier load-window narrio-tune
#
# Note: The `narrio tune` command creates sessions automatically,
# so you typically don't need to use tmuxifier. This example is provided
# for advanced users who want to customize their tmux layouts.

# Configuration
session_name="narrio-tune-custom"
input_file="${NARRIO_INPUT_FILE:-example.md}"
styles="${NARRIO_STYLES:-OpenAI,Anthropic,Google}"

# Parse styles into array
IFS=',' read -ra STYLE_ARRAY <<< "$styles"
num_styles=${#STYLE_ARRAY[@]}

# Create session
window_root "~/code/narrio"

# Create first window for variants
new_window "variants"

# Create panes based on number of styles
if [ "$num_styles" -eq 2 ]; then
    # 2 styles: vertical split
    split_h 50
elif [ "$num_styles" -eq 3 ]; then
    # 3 styles: one left, two stacked right
    split_h 50
    select_pane 1
    split_v 50
elif [ "$num_styles" -eq 4 ]; then
    # 4 styles: 2x2 grid
    split_h 50
    split_v 50
    select_pane 0
    split_v 50
fi

# Run commands in each pane
pane_index=0
for style in "${STYLE_ARRAY[@]}"; do
    select_pane $pane_index
    run_cmd "echo 'Running style: $style'"
    run_cmd "narrio run --content-type article --markdown $input_file --style $style"
    ((pane_index++))
done

# Create summary window
new_window "summary"
run_cmd "echo '=== Narrio Multi-Variant Tuning Pipeline ==='"
run_cmd "echo 'Input: $input_file'"
run_cmd "echo 'Styles: $styles'"
run_cmd "echo ''"
run_cmd "echo 'Check the variants window (Ctrl+b, 0) to see progress'"

# Select variants window by default
select_window 0
