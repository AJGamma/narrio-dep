# kitty-image-display Specification

## Purpose

Defines the image display capability that automatically presents generated images in the terminal using kitty's kittens protocol, with a Python PIL fallback for non-kitty terminals.

## Requirements

### Requirement: Kitty terminal detection
The system SHALL detect whether the current terminal supports kitty's image protocol before attempting to use `kitten icat`.

#### Scenario: Detect kitty via environment variable
- **WHEN** the `KITTY_LISTEN_ON` environment variable is set
- **THEN** the system determines that kitty is available

#### Scenario: Detect kitty via TERM variable
- **WHEN** the `TERM` environment variable equals `xterm-kitty`
- **THEN** the system determines that kitty is available

#### Scenario: Handle non-kitty terminal
- **WHEN** neither detection method succeeds
- **THEN** the system falls back to Python PIL display

### Requirement: kitten icat integration
The system SHALL use `kitten icat` to display images when kitty is detected.

#### Scenario: Display image with kitten icat
- **WHEN** an image file exists and kitty is available
- **THEN** the system executes `kitten icat --clear --transfer-mode=file <image-path>`

#### Scenario: Handle missing kitten command
- **WHEN** kitty is detected but `kitten` command is not found
- **THEN** the system falls back to Python PIL display with a warning message

### Requirement: Python PIL fallback
The system SHALL provide a fallback image display mechanism using Python PIL for non-kitty terminals.

#### Scenario: Open image with PIL and system viewer
- **WHEN** kitty is not available and PIL is installed
- **THEN** the system opens the image using `PIL.Image.show()` which launches the system's default image viewer

#### Scenario: Handle missing PIL
- **WHEN** PIL is not installed
- **THEN** the system displays the image path and offers to install Pillow with `pip install Pillow`

### Requirement: Image display configuration
The system SHALL support configuration for image display behavior.

#### Scenario: Configure max display size
- **WHEN** an image exceeds the configured max dimensions
- **THEN** the system scales it down before display while preserving aspect ratio

#### Scenario: Disable auto-display
- **WHEN** the user sets `--no-auto-display` flag
- **THEN** the system skips automatic image display and only prints the image path
