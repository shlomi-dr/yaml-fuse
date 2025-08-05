# YAML FUSE Filesystem

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/shlomi-dr/yaml-fuse/workflows/ci/badge.svg)](https://github.com/shlomi-dr/yaml-fuse/actions/workflows/ci.yml)
[![Quick Check](https://github.com/shlomi-dr/yaml-fuse/workflows/Quick%20Check/badge.svg)](https://github.com/shlomi-dr/yaml-fuse/actions/workflows/quick-check.yml)

A FUSE filesystem that maps YAML structure to a filesystem hierarchy. Each key in the YAML becomes a file or directory, and nested structures become subdirectories.

## Features

- **YAML to Filesystem Mapping**: Maps YAML structure to filesystem hierarchy
- **Multiple Output Formats**: Supports both YAML and JSON output formats
- **List Support**: Handles YAML lists as directories with numeric keys
- **Ephemeral Files**: Temporary files (starting with `.`) for scratch data
- **Auto-reload**: Automatically reloads YAML when source file changes
- **Format Preservation**: Preserves YAML formatting and structure
- **Verbatim Text**: Preserves exact string content including newlines, spaces, and formatting
- **Error Handling**: Robust error handling with logging
- **Comprehensive Testing**: Extensive test suite with unit, integration, and functional tests

## Installation

### Quick Install (Recommended)

Use the automated installer script for the easiest setup:

```bash
# Make the installer executable
chmod +x install.sh

# Run the installer
./install.sh
```

The installer will:
- ✅ Check for Python 3 and pip3
- ✅ Install Python dependencies from `requirements.txt`
- ✅ Detect your operating system (macOS/Linux)
- ✅ Guide you through FUSE installation with interactive prompts
- ✅ Provide smart detection for macFUSE on macOS
- ✅ Handle user group setup on Linux
- ✅ Give you clear next steps and verification instructions

### Manual Installation

If you prefer manual installation:

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. On Linux, install FUSE:
```bash
sudo apt-get install fuse  # Ubuntu/Debian
sudo yum install fuse      # CentOS/RHEL
```

3. On macOS, install FUSE:
   - **Recommended**: Download from the official website at [https://github.com/macfuse/macfuse/wiki/Getting-Started](https://github.com/macfuse/macfuse/wiki/Getting-Started)
   - **Note**: The official documentation recommends against using package managers. See [here](https://github.com/macfuse/macfuse/wiki/Getting-Started#:~:text=Please%20note%3A%20Although%20it%20is%20possible%20to%20install%20macFUSE%20using%20a%20package%20manager%20it%20is%20recommended%20to%20download%20the%20latest%20release%20from%20the%20macFUSE%20website%20instead.%20The%20macFUSE%20packages%20available%20through%20package%20managers%20are%20not%20managed%20by%20the%20macFUSE%20developers.) for details. You will also have to enable a kernel extension feature by rebooting your machine (one time).
   - **Alternative**: Use Homebrew (may install outdated version):
     ```bash
     brew install macfuse
     ```

## Usage

### Basic Usage

```bash
python yaml-fuse.py <yaml_file> <mount_point> [--mode yaml|json]
```

### Examples

1. Mount a YAML file with default YAML mode:
```bash
python yaml-fuse.py config.yaml /mnt/config
```

2. Mount with JSON output mode:
```bash
python yaml-fuse.py data.yaml /tmp/data --mode json
```

3. Enable debug logging:
```bash
python yaml-fuse.py config.yaml /mnt/config --debug
```

4. Run tests to verify installation:
```bash
# Quick test (no FUSE required)
python3 test_yaml_fuse.py --unit

# Full test suite (requires FUSE - for local development)
python3 test_yaml_fuse.py --all
```

**Note**: The CI pipeline runs unit tests and demos automatically. Full integration tests with FUSE filesystem mounting are designed for local development and testing.

## How It Works

### YAML Structure Mapping

Given a YAML file like:
```yaml
database:
  host: localhost
  port: 5432
  credentials:
    username: admin
    password: secret
servers:
  - name: web1
    ip: 192.168.1.10
  - name: web2
    ip: 192.168.1.11
applies_to:
  - production
  - staging
  - development
allowed_ips:
  - 192.168.1.0/24
  - 10.0.0.0/8
  - 172.16.0.0/12
features:
  - authentication
  - authorization
  - logging
  - monitoring
  - backup
```

The filesystem structure becomes:
```
/mount_point/
├── database/
│   ├── host
│   ├── port
│   └── credentials/
│       ├── username
│       └── password
├── servers/
│   ├── 0/
│   │   ├── name
│   │   └── ip
│   └── 1/
│       ├── name
│       └── ip
├── applies_to
├── allowed_ips
└── features
```

### File Access Modes

- **Default**: Access values as-is
- **YAML mode**: Append `.yaml` or `.yml` to get YAML-formatted output
- **JSON mode**: Append `.json` to get JSON-formatted output

Examples:
```bash
# Read raw value
cat /mnt/config/database/host

# Read as YAML
cat /mnt/config/database/credentials.yaml

# Read as JSON
cat /mnt/config/database/credentials.json

# Read list as YAML
cat /mnt/config/applies_to.yaml
# Output:
# - production
# - staging
# - development

# Read IP list
cat /mnt/config/allowed_ips.yaml
# Output:
# - 192.168.1.0/24
# - 10.0.0.0/8
# - 172.16.0.0/12

# Read features list
cat /mnt/config/features.yaml
# Output:
# - authentication
# - authorization
# - logging
# - monitoring
# - backup
```

### Ephemeral Files

Files starting with `.` are ephemeral and don't persist to the YAML file:
```bash
# Create temporary file
echo "temp data" > /mnt/config/.temp_file

# This file won't be saved to the YAML
```

## File Operations

### Reading
- Read files to get YAML values
- Use `.yaml` or `.json` suffix for formatted output
- Directories can be listed with `ls`

### Writing
- Write to files to update YAML values
- Create new files to add new keys
- Create directories to add nested structures

### Creating/Deleting
- `mkdir` creates new nested structures
- `rm` removes keys from YAML
- `touch` creates new files

## Error Handling

The tool includes comprehensive error handling:
- Graceful handling of malformed YAML
- File not found errors
- Permission errors
- Invalid path errors

## Logging

Enable debug logging with `--debug` flag:
```bash
python yaml-fuse.py config.yaml /mnt/config --debug
```

## Limitations

- Only supports basic YAML types (dict, list, str, int, float, bool)
- Complex YAML features like anchors/aliases are not supported
- File permissions are simplified (644 for files, 755 for directories)
- Concurrent access may have race conditions

## Text Preservation

The tool preserves exact string content including:
- Newlines and line breaks
- Leading and trailing spaces
- Indentation and formatting
- Empty lines
- Special characters

**String Output Format**: Strings are output as raw content. Block style (`|`) is only used for strings with multiple actual lines, not for strings with newline characters that are still single lines.

This is especially useful for:
- Documentation files
- Code examples
- Configuration templates
- Markdown content

## Troubleshooting

### Permission Denied
Make sure you have FUSE installed and your user is in the `fuse` group:
```bash
sudo usermod -a -G fuse $USER
```

### Mount Point Issues
Ensure the mount point exists and is a directory:
```bash
mkdir -p /mnt/config
```

### YAML Parsing Errors
Check your YAML file for syntax errors:
```bash
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

## Development

### Testing

The project includes comprehensive testing with multiple test suites:

#### Quick Test Commands
```bash
# Run unit tests (no FUSE required, CI/CD friendly)
python3 test_yaml_fuse.py --unit

# Run integration tests (requires FUSE)
sudo python3 test_yaml_fuse.py --integration

# Run all tests
python3 test_yaml_fuse.py --all

# Run demo functionality
python3 test_yaml_fuse.py --demo

# Run original functional tests
python3 functional_tests.py
```

#### Test Coverage

**Unit Tests** (`test_yaml_fuse.py`):
- YAML parsing logic and structure detection
- Path resolution and filesystem operations
- Cache invalidation and error handling
- Content generation and block style dumper
- Simulated filesystem operations

**Integration Tests** (`test_yaml_fuse.py`):
- File creation, reading, updating, deletion
- Directory creation and deletion
- YAML structure parsing and validation
- Cache invalidation for immediate updates
- Concurrent access and error handling

**Functional Tests** (`functional_tests.py`):
- Real FUSE mount/unmount behavior
- Specific YAML saving edge cases
- Actual filesystem operations
- Comprehensive functional validation

#### Manual Testing
```bash
# Create test YAML
echo "test: value" > test.yaml

# Mount and test
python yaml-fuse.py test.yaml /tmp/test &
sleep 2
ls /tmp/test
cat /tmp/test/test
umount /tmp/test
```

For detailed testing documentation, see [TESTING.md](TESTING.md).

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the MIT License. See [LICENSE](LICENSE) file for details.

The MIT License is one of the most permissive open source licenses, allowing you to:
- Use the software for any purpose
- Modify the software
- Distribute the software
- Use it commercially
- Sublicense it

The only requirement is that you include the original copyright notice and license text in any copies or substantial portions of the software. 