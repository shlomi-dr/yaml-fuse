# YAML-FUSE Testing Guide

This document describes the testing infrastructure for the yaml-fuse filesystem.

## Test Structure

The testing suite consists of two complementary test files:

### Main Test File (`test_yaml_fuse.py`)
- **Purpose**: Comprehensive unit/integration test suite with proper test framework
- **Requirements**: Python 3.x, PyYAML (FUSE optional for integration tests)
- **Features**:
  - Unit tests (no FUSE required)
  - Integration tests (requires FUSE)
  - Demo functionality
  - Built-in test runner with command-line options

### Functional Test File (`functional_tests.py`)
- **Purpose**: Functional tests that test actual FUSE behavior and edge cases
- **Requirements**: Python 3.x, PyYAML, FUSE, root privileges
- **Features**:
  - Real FUSE mount/unmount testing
  - Specific YAML saving edge cases
  - Actual filesystem operations
  - Comprehensive functional validation

## Running Tests

### CI Tests (Automated)
The CI pipeline runs these tests automatically:
```bash
# Unit tests (no FUSE required)
python3 tests.py --unit

# Demo functionality
python3 tests.py --demo

# Code style checks
flake8 yaml-fuse.py tests.py --max-line-length=120 --ignore=E501,W503,W291,W293,E302,E305,F401,F841,F541,E301,E128,W292,E722

# Security scans
bandit -r . --skip B404,B603,B607,B108,B110
```

### Local Development Tests
For full testing including FUSE filesystem operations:
```bash
# Run all tests (requires FUSE)
python3 tests.py --all

# Run specific test types
python3 tests.py --integration  # FUSE integration tests
python3 tests.py --unit         # Unit tests only
python3 tests.py --demo         # Demo functionality

# Direct test execution
python3 -m unittest tests -v
```

### Test Strategy
- **CI Tests**: Unit tests, demos, and code quality checks (no FUSE required)
- **Local Tests**: Full integration and functional tests with actual FUSE mounting
- **Why Separate**: FUSE filesystem mounting is complex in CI environments and requires specific system permissions

## Test Coverage

### Unit Tests Coverage (`TestYAMLFuseUnit`)

| Component | Test Cases | Description |
|-----------|------------|-------------|
| YAML Parsing | `test_yaml_parsing_logic` | Tests parsing of different content types |
| Block Style Dumper | `test_block_style_dumper` | Tests YAML formatting |
| Path Resolution | `test_path_resolution` | Tests filesystem path resolution |
| Suffix Stripping | `test_strip_suffix` | Tests file extension handling |
| Ephemeral Files | `test_ephemeral_file_detection` | Tests hidden file detection |
| Content Generation | `test_get_value_content` | Tests content serialization |
| Cache Invalidation | `test_cache_invalidation` | Tests cache management |
| YAML Reloading | `test_yaml_reloading` | Tests file change detection |
| Error Handling | `test_error_handling` | Tests error scenarios |
| Simulated Operations | `test_simulated_*` | Tests simulated filesystem operations |

### Integration Tests Coverage (`TestYAMLFuseIntegration`)

| Feature | Test Cases | Description |
|---------|------------|-------------|
| Basic Operations | `test_basic_file_operations` | Create, read, delete files |
| YAML Structure | `test_yaml_structure_parsing` | YAML content becomes directories |
| List Handling | `test_list_parsing` | YAML lists become files |
| Multiline Strings | `test_multiline_string_preservation` | Invalid YAML preserved as strings |
| Directory Operations | `test_directory_operations` | Create and delete directories |
| Cache Invalidation | `test_cache_invalidation` | Immediate updates after operations |
| Complex Structures | `test_nested_yaml_structure` | Complex nested YAML handling |
| File Updates | `test_file_updates` | Update existing files |
| Empty Files | `test_empty_file_handling` | Handle empty file content |
| Special Characters | `test_special_characters` | Handle special characters |
| JSON Mode | `test_json_mode` | JSON file handling |
| Error Handling | `test_error_handling` | Invalid operations |
| Concurrent Access | `test_concurrent_access` | Multi-threaded operations |

### Demo Tests Coverage (`TestYAMLFuseDemo`)

| Feature | Test Cases | Description |
|---------|------------|-------------|
| YAML Parsing Demo | `test_yaml_parsing_demo` | Demonstrates YAML parsing functionality |
| Cache Invalidation Demo | `test_cache_invalidation_demo` | Demonstrates cache invalidation |

## Key Test Scenarios

### 1. YAML Content Parsing
```yaml
# Should become a directory
plugins:
  providers:
  - name: example
    path: ../../bin

# Should become a file with list content
- item1
- item2
- item3

# Should remain a string
This is a simple string

# Should remain a multiline string
This is a multiline
string that should be
preserved as a string.
```

### 2. Cache Invalidation
- File creation immediately updates directory listing
- File deletion immediately removes from directory listing
- Directory creation immediately appears in listing
- File updates immediately reflect changes

### 3. Error Handling
- Non-existent files return appropriate errors
- Invalid YAML content is handled gracefully
- Invalid paths are handled correctly
- Concurrent access is thread-safe

## Test Environment Setup

### Prerequisites
```bash
# Install required packages
pip install PyYAML

# For integration tests (macOS)
brew install macfuse

# For integration tests (Linux)
sudo apt-get install fuse
```

### Running in CI/CD
```yaml
# Example GitHub Actions workflow
name: Test yaml-fuse
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    - name: Install dependencies
      run: |
        pip install PyYAML
    - name: Run unit tests
      run: python3 test_yaml_fuse.py --unit
    - name: Run integration tests
      run: |
        sudo apt-get update
        sudo apt-get install -y fuse
        sudo python3 test_yaml_fuse.py --integration
```

## Debugging Tests

### Enable Debug Logging
```bash
# Run with debug output
python3 yaml-fuse.py example.yaml /tmp/test --debug
```

### Common Issues

1. **FUSE Mount Permission Denied**
   - Ensure you have root privileges
   - Check if FUSE is properly installed
   - Verify mount point permissions

2. **Tests Hanging**
   - Check for existing FUSE mounts
   - Kill any hanging yaml-fuse processes
   - Clean up temporary directories

3. **Import Errors**
   - Ensure all dependencies are installed
   - Check Python path configuration
   - Verify file permissions

## Adding New Tests

### Unit Test Example
```python
def test_new_feature(self):
    """Test description"""
    # Setup
    test_data = "test content"
    
    # Execute
    result = self.fuse._some_method(test_data)
    
    # Assert
    self.assertEqual(result, expected_value)
```

### Integration Test Example
```python
def test_new_filesystem_feature(self):
    """Test new filesystem feature"""
    # Create test file
    test_file = os.path.join(self.mount_point, 'test')
    with open(test_file, 'w') as f:
        f.write('test content')
    
    # Verify behavior
    self.assertTrue(os.path.exists(test_file))
    
    # Check YAML file
    yaml_data = self.read_yaml_file()
    self.assertIn('test', yaml_data)
```

## Performance Testing

### Benchmark Tests
```python
def test_performance_large_files(self):
    """Test performance with large files"""
    import time
    
    start_time = time.time()
    
    # Create large file
    large_content = "x" * 1000000
    test_file = os.path.join(self.mount_point, 'large')
    with open(test_file, 'w') as f:
        f.write(large_content)
    
    end_time = time.time()
    self.assertLess(end_time - start_time, 5.0)  # Should complete within 5 seconds
```

## Continuous Integration

The test suite is designed to work in CI/CD environments:

- Unit tests run without special privileges
- Integration tests can be run with sudo in CI
- Demo script provides quick functionality verification
- Comprehensive error handling and cleanup

## Contributing

When adding new features:

1. Add unit tests for the core logic
2. Add integration tests for filesystem behavior
3. Update the demo script if applicable
4. Ensure all tests pass before submitting

## Troubleshooting

### Test Failures

1. **Unit Test Failures**
   - Check Python dependencies
   - Verify test data setup
   - Review assertion logic

2. **Integration Test Failures**
   - Check FUSE installation
   - Verify mount point permissions
   - Clean up existing mounts

3. **Demo Failures**
   - Check YAML parsing logic
   - Verify file operations
   - Review output expectations

For more detailed debugging, run tests with verbose output:
```bash
python3 -v test_unit.py
``` 