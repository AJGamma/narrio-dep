# Narrio Tmux Configuration Examples

This directory contains example tmux configurations for the `narrio tune` multi-variant pipeline.

## Files

### `narrio-tune-simple.sh`

A standalone bash script that demonstrates how the `narrio tune` command works under the hood.

**Usage:**
```bash
chmod +x narrio-tune-simple.sh
./narrio-tune-simple.sh <input-file> <style1,style2,style3>
```

**Example:**
```bash
./narrio-tune-simple.sh article.md "OpenAI,Anthropic,Google"
```

This is useful for:
- Understanding how narrio tune uses tmux
- Creating custom wrapper scripts
- Debugging tmux session issues

### `narrio-tune.tmuxifier.sh`

An example layout file for [tmuxifier](https://github.com/jimeh/tmuxifier), a tmux layout manager.

**Setup:**
1. Install tmuxifier: `brew install tmuxifier` (or see tmuxifier docs)
2. Copy to your layouts directory:
   ```bash
   cp narrio-tune.tmuxifier.sh ~/.tmuxifier/layouts/narrio-tune.window.sh
   ```
3. Set environment variables and load:
   ```bash
   export NARRIO_INPUT_FILE="article.md"
   export NARRIO_STYLES="OpenAI,Anthropic,Google"
   tmuxifier load-window narrio-tune
   ```

This is useful for:
- Reusable session templates
- Integration with existing tmuxifier workflows
- Advanced customization beyond `narrio tune`

## Do You Need These?

**Short answer: Probably not.**

The `narrio tune` command automatically creates and manages tmux sessions for you. These examples are provided for:

1. **Educational purposes**: Understanding how the tool works
2. **Advanced customization**: Building your own custom workflows
3. **Troubleshooting**: Debugging or modifying the tmux behavior

For normal usage, just use:
```bash
narrio tune --input article.md --styles OpenAI,Anthropic,Google
```

## Related Documentation

- [Tune Command Documentation](../../docs/tune-command.md)
- [Tmux Documentation](https://github.com/tmux/tmux/wiki)
- [Tmuxifier Project](https://github.com/jimeh/tmuxifier)

## Contributing

If you create useful tmux configurations for narrio, feel free to contribute them as examples!
