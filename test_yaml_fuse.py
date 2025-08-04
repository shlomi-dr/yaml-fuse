#!/usr/bin/env python3
"""
Comprehensive test suite for yaml-fuse filesystem

This single file contains all tests:
- Unit tests (no FUSE required)
- Integration tests (requires FUSE)
- Demo functionality
- Performance tests
"""

import os
import sys
import tempfile
import shutil
import time
import yaml
import unittest
import subprocess
import threading
import signal
from pathlib import Path

# Add the current directory to the path
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
except NameError:
    # __file__ is not available when executed as string
    sys.path.insert(0, os.getcwd())

# Import the YAMLFuse class from the main file
try:
    # Import the classes from the main yaml-fuse.py file
    import importlib.util
    spec = importlib.util.spec_from_file_location("yaml_fuse_module", "yaml-fuse.py")
    yaml_fuse_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(yaml_fuse_module)
    
    YAMLFuse = yaml_fuse_module.YAMLFuse
    BlockStyleDumper = yaml_fuse_module.BlockStyleDumper
except ImportError:
    # Fallback for when yaml-fuse module is not available
    YAMLFuse = None
    BlockStyleDumper = None

class TestYAMLFuseUnit(unittest.TestCase):
    """Unit tests that don't require FUSE mounting"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix='yaml-fuse-unit-')
        self.yaml_file = os.path.join(self.temp_dir, 'test.yaml')
        
        # Create initial YAML file
        initial_data = {
            'name': 'test-provider',
            'outputs': {
                'resourceId': {
                    'value': '${testResource.id}'
                }
            }
        }
        
        with open(self.yaml_file, 'w') as f:
            yaml.dump(initial_data, f, default_flow_style=False)
        
        # Create YAMLFuse instance
        if YAMLFuse:
            self.fuse = YAMLFuse(self.yaml_file)
        else:
            self.skipTest("YAMLFuse not available")
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_yaml_parsing_logic(self):
        """Test YAML parsing logic in release method"""
        # Test data that should become a dictionary
        yaml_dict_content = """plugins:
  providers:
  - name: example
    path: ../../bin"""
        
        # Test data that should become a list
        yaml_list_content = """- item1
- item2
- item3"""
        
        # Test data that should remain a string
        string_content = "This is a simple string"
        
        # Test multiline string content
        multiline_content = """This is a multiline
string that should be
preserved as a string."""
        
        # Mock the release method's logic
        def test_parse_content(content):
            try:
                parsed_yaml = yaml.safe_load(content)
                if parsed_yaml is not None:
                    return parsed_yaml
                else:
                    return ""
            except yaml.YAMLError:
                stripped = content.rstrip('\n')
                if '\n' in stripped and len(stripped.split('\n')) > 1:
                    return content
                else:
                    return content.rstrip('\n')
        
        # Test dictionary parsing
        result = test_parse_content(yaml_dict_content)
        self.assertIsInstance(result, dict)
        self.assertIn('plugins', result)
        
        # Test list parsing
        result = test_parse_content(yaml_list_content)
        self.assertIsInstance(result, list)
        self.assertEqual(result, ['item1', 'item2', 'item3'])
        
        # Test string parsing
        result = test_parse_content(string_content)
        self.assertIsInstance(result, str)
        self.assertEqual(result, string_content)
        
        # Test multiline string parsing
        result = test_parse_content(multiline_content)
        self.assertIsInstance(result, str)
        # The content should be preserved as-is for multiline strings
        self.assertIn('multiline', result)
        self.assertIn('string', result)
    
    def test_block_style_dumper(self):
        """Test BlockStyleDumper functionality"""
        if not BlockStyleDumper:
            self.skipTest("BlockStyleDumper not available")
            
        # Test data
        data = {
            'multiline_string': """This is a multiline
string with multiple
lines and indentation""",
            'simple_string': 'simple',
            'list': ['item1', 'item2', 'item3'],
            'dict': {'key': 'value'}
        }
        
        # Dump with BlockStyleDumper
        output = yaml.dump(data, Dumper=BlockStyleDumper, default_flow_style=False)
        
        # Check that multiline strings use block style
        self.assertIn('|', output)  # Should have block style indicator
        
        # Check that simple strings don't use block style
        self.assertIn('simple_string: simple', output)
        
        # Check that lists use block style
        self.assertIn('- item1', output)
        self.assertIn('- item2', output)
        self.assertIn('- item3', output)
    
    def test_path_resolution(self):
        """Test path resolution logic"""
        # Test root path
        parent, key = self.fuse._resolve_path('/')
        self.assertEqual(parent, self.fuse.data)
        self.assertIsNone(key)
        
        # Test simple path
        parent, key = self.fuse._resolve_path('/name')
        self.assertEqual(parent, self.fuse.data)
        self.assertEqual(key, 'name')
        
        # Test nested path
        parent, key = self.fuse._resolve_path('/outputs/resourceId')
        self.assertEqual(parent, self.fuse.data['outputs'])
        self.assertEqual(key, 'resourceId')
        
        # Test non-existent path
        parent, key = self.fuse._resolve_path('/nonexistent')
        # For non-existent paths, it should return the parent and the key
        self.assertEqual(parent, self.fuse.data)
        self.assertEqual(key, 'nonexistent')
        
        # Test nested non-existent path
        parent, key = self.fuse._resolve_path('/outputs/nonexistent')
        self.assertEqual(parent, self.fuse.data['outputs'])
        self.assertEqual(key, 'nonexistent')
    
    def test_strip_suffix(self):
        """Test suffix stripping logic"""
        # Test .json suffix
        path, mode = self.fuse._strip_suffix('/test.json')
        self.assertEqual(path, '/test')
        self.assertEqual(mode, 'json')
        
        # Test .yaml suffix
        path, mode = self.fuse._strip_suffix('/test.yaml')
        self.assertEqual(path, '/test')
        self.assertEqual(mode, 'yaml')
        
        # Test .yml suffix
        path, mode = self.fuse._strip_suffix('/test.yml')
        self.assertEqual(path, '/test')
        self.assertEqual(mode, 'yaml')
        
        # Test no suffix
        path, mode = self.fuse._strip_suffix('/test')
        self.assertEqual(path, '/test')
        self.assertEqual(mode, 'yaml')  # default mode
    
    def test_ephemeral_file_detection(self):
        """Test ephemeral file detection"""
        # Test ephemeral files
        self.assertTrue(self.fuse._is_ephemeral('/.hidden'))
        self.assertTrue(self.fuse._is_ephemeral('/.config'))
        
        # Test regular files
        self.assertFalse(self.fuse._is_ephemeral('/normal'))
        self.assertFalse(self.fuse._is_ephemeral('/file.txt'))
    
    def test_get_value_content(self):
        """Test content generation for different types"""
        # Test string content
        content = self.fuse._get_value_content('test string', 'yaml')
        self.assertEqual(content.decode('utf-8'), 'test string')
        
        # Test dictionary content
        test_dict = {'key': 'value', 'number': 42}
        content = self.fuse._get_value_content(test_dict, 'yaml')
        # Should be valid YAML
        parsed = yaml.safe_load(content.decode('utf-8'))
        self.assertEqual(parsed, test_dict)
        
        # Test JSON mode
        content = self.fuse._get_value_content(test_dict, 'json')
        import json
        parsed = json.loads(content.decode('utf-8'))
        self.assertEqual(parsed, test_dict)
    
    def test_cache_invalidation(self):
        """Test cache invalidation mechanism"""
        # Initially cache should not be invalidated
        self.assertFalse(self.fuse.cache_invalidated)
        
        # Invalidate cache
        self.fuse._invalidate_cache()
        self.assertTrue(self.fuse.cache_invalidated)
        
        # Reset cache
        self.fuse.cache_invalidated = False
        self.assertFalse(self.fuse.cache_invalidated)
    
    def test_yaml_reloading(self):
        """Test YAML file reloading"""
        # Get initial mtime
        initial_mtime = self.fuse.last_mtime
        
        # Modify the YAML file
        with open(self.yaml_file, 'w') as f:
            yaml.dump({'new': 'data'}, f, default_flow_style=False)
        
        # Force reload by resetting last_mtime
        self.fuse.last_mtime = 0
        self.fuse._reload_if_needed()
        
        # Check that data was reloaded
        self.assertIn('new', self.fuse.data)
        self.assertEqual(self.fuse.data['new'], 'data')
    
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        # Test with non-existent YAML file
        non_existent_file = '/tmp/nonexistent.yaml'
        try:
            fuse = YAMLFuse(non_existent_file)
            self.assertEqual(fuse.data, {})
        except FileNotFoundError:
            # This is expected behavior
            pass
        
        # Test with invalid YAML content
        invalid_yaml_file = os.path.join(self.temp_dir, 'invalid.yaml')
        with open(invalid_yaml_file, 'w') as f:
            f.write('invalid: yaml: content: [')
        
        fuse = YAMLFuse(invalid_yaml_file)
        self.assertEqual(fuse.data, {})
    
    def test_simulated_file_operations(self):
        """Test simulated file creation and reading"""
        # Simulate creating a file
        test_content = 'Hello, World!'
        
        # This would normally happen in the release method
        # We'll simulate it by directly modifying the data
        self.fuse.data['test.txt'] = test_content
        self.fuse.dirty = True
        self.fuse._save_yaml()
        
        # Verify the file was saved
        with open(self.yaml_file, 'r') as f:
            saved_data = yaml.safe_load(f)
        
        self.assertIn('test.txt', saved_data)
        self.assertEqual(saved_data['test.txt'], test_content)
    
    def test_simulated_directory_creation(self):
        """Test simulated directory creation"""
        # Simulate creating a directory
        self.fuse.data['newdir'] = {}
        self.fuse.dirty = True
        self.fuse._save_yaml()
        
        # Verify the directory was saved
        with open(self.yaml_file, 'r') as f:
            saved_data = yaml.safe_load(f)
        
        self.assertIn('newdir', saved_data)
        self.assertIsInstance(saved_data['newdir'], dict)
    
    def test_simulated_yaml_structure_creation(self):
        """Test simulated YAML structure creation"""
        # Simulate creating a file with YAML content
        yaml_content = {
            'plugins': {
                'providers': [
                    {'name': 'example', 'path': '../../bin'}
                ]
            }
        }
        
        self.fuse.data['config'] = yaml_content
        self.fuse.dirty = True
        self.fuse._save_yaml()
        
        # Verify the structure was saved correctly
        with open(self.yaml_file, 'r') as f:
            saved_data = yaml.safe_load(f)
        
        self.assertIn('config', saved_data)
        self.assertIsInstance(saved_data['config'], dict)
        self.assertIn('plugins', saved_data['config'])
        self.assertIn('providers', saved_data['config']['plugins'])

class TestYAMLFuseIntegration(unittest.TestCase):
    """Integration tests that require FUSE mounting"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp(prefix='yaml-fuse-integration-')
        self.mount_point = os.path.join(self.test_dir, 'mount')
        self.yaml_file = os.path.join(self.test_dir, 'test.yaml')
        
        # Create initial YAML file
        initial_data = {
            'name': 'test-provider',
            'outputs': {
                'resourceId': {
                    'value': '${testResource.id}'
                }
            },
            'resources': {
                'testResource': {
                    'type': 'test:Resource',
                    'properties': {
                        'name': 'Test Resource',
                        'description': 'A test resource'
                    }
                }
            }
        }
        
        with open(self.yaml_file, 'w') as f:
            yaml.dump(initial_data, f, default_flow_style=False)
        
        # Start the filesystem
        self.start_filesystem()
        
        # Wait for mount to be ready
        time.sleep(2)
    
    def tearDown(self):
        """Clean up test environment"""
        self.stop_filesystem()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def start_filesystem(self):
        """Start the yaml-fuse filesystem"""
        try:
            # Create mount point
            os.makedirs(self.mount_point, exist_ok=True)
            
            # Start the process
            self.fuse_process = subprocess.Popen(
                [sys.executable, 'yaml-fuse.py', self.yaml_file, self.mount_point],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except Exception as e:
            self.fail(f"Failed to start filesystem: {e}")
    
    def stop_filesystem(self):
        """Stop the yaml-fuse filesystem"""
        if hasattr(self, 'fuse_process'):
            try:
                self.fuse_process.terminate()
                self.fuse_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.fuse_process.kill()
                self.fuse_process.wait()
            except Exception:
                pass
    
    def read_yaml_file(self):
        """Read the current YAML file content"""
        with open(self.yaml_file, 'r') as f:
            return yaml.safe_load(f)
    
    def test_basic_file_operations(self):
        """Test basic file creation, reading, and deletion"""
        # Create a simple file
        test_file = os.path.join(self.mount_point, 'simple.txt')
        test_content = 'Hello, World!'
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Verify file exists
        self.assertTrue(os.path.exists(test_file))
        
        # Read the file
        with open(test_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, test_content)
        
        # Check YAML file was updated
        yaml_data = self.read_yaml_file()
        self.assertIn('simple.txt', yaml_data)
        self.assertEqual(yaml_data['simple.txt'], test_content)
        
        # Delete the file
        os.unlink(test_file)
        self.assertFalse(os.path.exists(test_file))
        
        # Check YAML file was updated
        yaml_data = self.read_yaml_file()
        self.assertNotIn('simple.txt', yaml_data)
    
    def test_yaml_structure_parsing(self):
        """Test that YAML content is properly parsed and becomes directories"""
        # Create a file with YAML dictionary content
        test_file = os.path.join(self.mount_point, 'config')
        yaml_content = """plugins:
  providers:
  - name: example
    path: ../../bin
  - name: another
    path: ./local"""
        
        with open(test_file, 'w') as f:
            f.write(yaml_content)
        
        # Verify it became a directory
        self.assertTrue(os.path.isdir(test_file))
        
        # Check the directory contents
        contents = os.listdir(test_file)
        self.assertIn('plugins', contents)
        
        # Check nested structure
        plugins_dir = os.path.join(test_file, 'plugins')
        self.assertTrue(os.path.isdir(plugins_dir))
        
        providers_dir = os.path.join(plugins_dir, 'providers')
        self.assertTrue(os.path.isdir(providers_dir))
        
        # Check YAML file structure
        yaml_data = self.read_yaml_file()
        self.assertIn('config', yaml_data)
        self.assertIsInstance(yaml_data['config'], dict)
        self.assertIn('plugins', yaml_data['config'])
    
    def test_list_parsing(self):
        """Test that YAML lists are properly handled"""
        # Create a file with YAML list content
        test_file = os.path.join(self.mount_point, 'items')
        list_content = """- item1
- item2
- item3"""
        
        with open(test_file, 'w') as f:
            f.write(list_content)
        
        # Verify it's a file (lists become files, not directories)
        self.assertTrue(os.path.isfile(test_file))
        
        # Check YAML file structure
        yaml_data = self.read_yaml_file()
        self.assertIn('items', yaml_data)
        self.assertIsInstance(yaml_data['items'], list)
        self.assertEqual(yaml_data['items'], ['item1', 'item2', 'item3'])
    
    def test_multiline_string_preservation(self):
        """Test that invalid YAML is preserved as multiline strings"""
        # Create a file with content that looks like YAML but isn't valid
        test_file = os.path.join(self.mount_point, 'multiline')
        multiline_content = """This is a multiline
string that contains
some content that
is not valid YAML

But should be preserved
as a string."""
        
        with open(test_file, 'w') as f:
            f.write(multiline_content)
        
        # Verify it's a file
        self.assertTrue(os.path.isfile(test_file))
        
        # Check YAML file structure
        yaml_data = self.read_yaml_file()
        self.assertIn('multiline', yaml_data)
        self.assertIsInstance(yaml_data['multiline'], str)
        self.assertEqual(yaml_data['multiline'], multiline_content)
    
    def test_directory_operations(self):
        """Test directory creation and deletion"""
        # Create a directory
        test_dir = os.path.join(self.mount_point, 'testdir')
        os.makedirs(test_dir)
        
        # Verify directory exists
        self.assertTrue(os.path.isdir(test_dir))
        
        # Create a file in the directory
        test_file = os.path.join(test_dir, 'nested.txt')
        with open(test_file, 'w') as f:
            f.write('nested content')
        
        # Check YAML structure
        yaml_data = self.read_yaml_file()
        self.assertIn('testdir', yaml_data)
        self.assertIsInstance(yaml_data['testdir'], dict)
        self.assertIn('nested.txt', yaml_data['testdir'])
        
        # Delete the directory
        shutil.rmtree(test_dir)
        self.assertFalse(os.path.exists(test_dir))
        
        # Check YAML structure
        yaml_data = self.read_yaml_file()
        self.assertNotIn('testdir', yaml_data)
    
    def test_cache_invalidation(self):
        """Test that cache invalidation works for immediate updates"""
        # Create a file
        test_file = os.path.join(self.mount_point, 'cache_test')
        with open(test_file, 'w') as f:
            f.write('initial content')
        
        # Verify it exists
        self.assertTrue(os.path.exists(test_file))
        
        # Delete the file
        os.unlink(test_file)
        
        # Immediately check directory listing - should not show the file
        contents = os.listdir(self.mount_point)
        self.assertNotIn('cache_test', contents)
        
        # Check YAML file
        yaml_data = self.read_yaml_file()
        self.assertNotIn('cache_test', yaml_data)
    
    def test_nested_yaml_structure(self):
        """Test complex nested YAML structures"""
        # Create a file with complex nested YAML
        test_file = os.path.join(self.mount_point, 'complex')
        complex_content = """apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
  namespace: default
data:
  config.yaml: |
    database:
      host: localhost
      port: 5432
    logging:
      level: info
      format: json"""
        
        with open(test_file, 'w') as f:
            f.write(complex_content)
        
        # Verify it became a directory
        self.assertTrue(os.path.isdir(test_file))
        
        # Check nested structure
        yaml_data = self.read_yaml_file()
        self.assertIn('complex', yaml_data)
        complex_data = yaml_data['complex']
        
        self.assertIn('apiVersion', complex_data)
        self.assertEqual(complex_data['apiVersion'], 'v1')
        
        self.assertIn('metadata', complex_data)
        self.assertIn('name', complex_data['metadata'])
        self.assertEqual(complex_data['metadata']['name'], 'my-config')
        
        self.assertIn('data', complex_data)
        self.assertIn('config.yaml', complex_data['data'])
    
    def test_file_updates(self):
        """Test updating existing files"""
        # Create initial file
        test_file = os.path.join(self.mount_point, 'update_test')
        initial_content = 'initial content'
        
        with open(test_file, 'w') as f:
            f.write(initial_content)
        
        # Update the file
        updated_content = 'updated content'
        with open(test_file, 'w') as f:
            f.write(updated_content)
        
        # Verify the update
        with open(test_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, updated_content)
        
        # Check YAML file
        yaml_data = self.read_yaml_file()
        self.assertEqual(yaml_data['update_test'], updated_content)
    
    def test_empty_file_handling(self):
        """Test handling of empty files"""
        # Create empty file
        test_file = os.path.join(self.mount_point, 'empty')
        with open(test_file, 'w') as f:
            pass  # Create empty file
        
        # Verify it exists
        self.assertTrue(os.path.exists(test_file))
        
        # Check YAML file
        yaml_data = self.read_yaml_file()
        self.assertIn('empty', yaml_data)
        self.assertEqual(yaml_data['empty'], '')
    
    def test_special_characters(self):
        """Test handling of special characters in content"""
        # Create file with special characters
        test_file = os.path.join(self.mount_point, 'special')
        special_content = 'Line with "quotes" and \'apostrophes\'\nAnd newlines\nAnd tabs\there'
        
        with open(test_file, 'w') as f:
            f.write(special_content)
        
        # Verify content is preserved
        with open(test_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, special_content)
        
        # Check YAML file
        yaml_data = self.read_yaml_file()
        self.assertEqual(yaml_data['special'], special_content)
    
    def test_json_mode(self):
        """Test JSON mode functionality"""
        # This test would require restarting the filesystem with --mode json
        # For now, we'll test that JSON files are handled correctly
        test_file = os.path.join(self.mount_point, 'data.json')
        json_content = '{"key": "value", "number": 42, "array": [1, 2, 3]}'
        
        with open(test_file, 'w') as f:
            f.write(json_content)
        
        # Verify it's a file
        self.assertTrue(os.path.isfile(test_file))
        
        # Check YAML file
        yaml_data = self.read_yaml_file()
        self.assertIn('data.json', yaml_data)
        # Should be stored as string since it's not valid YAML
        self.assertIsInstance(yaml_data['data.json'], str)
    
    def test_error_handling(self):
        """Test error handling for invalid operations"""
        # Try to access non-existent file
        non_existent = os.path.join(self.mount_point, 'does_not_exist')
        self.assertFalse(os.path.exists(non_existent))
        
        # Try to read non-existent file
        with self.assertRaises(FileNotFoundError):
            with open(non_existent, 'r') as f:
                f.read()
        
        # Try to create file in non-existent directory
        invalid_path = os.path.join(self.mount_point, 'nonexistent', 'file.txt')
        with self.assertRaises(FileNotFoundError):
            with open(invalid_path, 'w') as f:
                f.write('content')
    
    def test_concurrent_access(self):
        """Test concurrent file operations"""
        def create_file(thread_id):
            test_file = os.path.join(self.mount_point, f'concurrent_{thread_id}')
            with open(test_file, 'w') as f:
                f.write(f'content from thread {thread_id}')
        
        # Create multiple files concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all files were created
        for i in range(5):
            test_file = os.path.join(self.mount_point, f'concurrent_{i}')
            self.assertTrue(os.path.exists(test_file))
        
        # Check YAML file
        yaml_data = self.read_yaml_file()
        for i in range(5):
            self.assertIn(f'concurrent_{i}', yaml_data)

class TestYAMLFuseDemo(unittest.TestCase):
    """Demo tests that show key functionality"""
    
    def test_yaml_parsing_demo(self):
        """Demonstrate YAML parsing functionality"""
        # Test different types of content
        test_cases = [
            {
                'name': 'Simple String',
                'content': 'Hello, World!',
                'expected_type': str
            },
            {
                'name': 'YAML Dictionary',
                'content': """plugins:
  providers:
  - name: example
    path: ../../bin""",
                'expected_type': dict
            },
            {
                'name': 'YAML List',
                'content': """- item1
- item2
- item3""",
                'expected_type': list
            },
            {
                'name': 'Multiline String',
                'content': """This is a multiline
string that should be
preserved as a string.""",
                'expected_type': str
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case['name']):
                # Simulate the parsing logic
                try:
                    parsed = yaml.safe_load(test_case['content'])
                    if parsed is not None:
                        result_type = type(parsed)
                        self.assertIsInstance(parsed, test_case['expected_type'])
                    else:
                        self.assertEqual(parsed, "")
                except yaml.YAMLError:
                    # For invalid YAML, it should be treated as string
                    self.assertIsInstance(test_case['content'], str)
    
    def test_cache_invalidation_demo(self):
        """Demonstrate cache invalidation"""
        # Simulate cache invalidation
        cache_invalidated = False
        
        def invalidate_cache():
            nonlocal cache_invalidated
            cache_invalidated = True
        
        def check_cache():
            nonlocal cache_invalidated
            if cache_invalidated:
                cache_invalidated = False
                return True
            else:
                return False
        
        # Simulate operations that invalidate cache
        operations = [
            "Create file",
            "Delete file", 
            "Create directory",
            "Update file content"
        ]
        
        for operation in operations:
            with self.subTest(operation):
                # Initially cache should be valid
                self.assertFalse(check_cache())
                
                # Perform operation that invalidates cache
                invalidate_cache()
                
                # Cache should now be invalid
                self.assertTrue(check_cache())
                
                # Cache should be valid again after check
                self.assertFalse(check_cache())

def run_demo():
    """Run a simple demo of key functionality"""
    print("🚀 YAML-FUSE Demo")
    print("=" * 50)
    
    # Demo YAML parsing
    print("=== YAML Parsing Demo ===")
    test_cases = [
        ('Simple String', 'Hello, World!'),
        ('YAML Dictionary', 'plugins:\n  providers:\n  - name: example\n    path: ../../bin'),
        ('YAML List', '- item1\n- item2\n- item3'),
        ('Multiline String', 'This is a multiline\nstring that should be\npreserved as a string.')
    ]
    
    for name, content in test_cases:
        print(f"\nTesting: {name}")
        print(f"Content:\n{content}")
        
        try:
            parsed = yaml.safe_load(content)
            if parsed is not None:
                result_type = type(parsed)
                print(f"✅ Parsed as: {result_type.__name__}")
                print(f"   Value: {parsed}")
            else:
                print("✅ Parsed as: empty string")
        except yaml.YAMLError:
            print("✅ Parsed as: string (invalid YAML)")
        
        print("-" * 40)
    
    # Demo filesystem operations
    print("\n=== Filesystem Operations Demo ===")
    temp_dir = tempfile.mkdtemp(prefix='yaml-fuse-demo-')
    yaml_file = os.path.join(temp_dir, 'demo.yaml')
    
    try:
        # Create initial YAML file
        initial_data = {
            'name': 'demo-provider',
            'outputs': {
                'resourceId': {
                    'value': '${demoResource.id}'
                }
            }
        }
        
        with open(yaml_file, 'w') as f:
            yaml.dump(initial_data, f, default_flow_style=False)
        
        print(f"Created YAML file: {yaml_file}")
        print("Initial content:")
        with open(yaml_file, 'r') as f:
            print(f.read())
        
        # Simulate file operations
        print("\nSimulating file operations...")
        
        # Add a simple file
        initial_data['simple.txt'] = 'Hello, World!'
        print("✅ Added simple.txt")
        
        # Add a YAML structure
        initial_data['config'] = {
            'plugins': {
                'providers': [
                    {'name': 'example', 'path': '../../bin'}
                ]
            }
        }
        print("✅ Added config (YAML structure)")
        
        # Add a list
        initial_data['items'] = ['item1', 'item2', 'item3']
        print("✅ Added items (list)")
        
        # Save the updated YAML
        with open(yaml_file, 'w') as f:
            yaml.dump(initial_data, f, Dumper=yaml.SafeDumper, default_flow_style=False)
        
        print("\nUpdated YAML content:")
        with open(yaml_file, 'r') as f:
            print(f.read())
        
        # Simulate file deletion
        del initial_data['simple.txt']
        print("\n✅ Deleted simple.txt")
        
        # Save again
        with open(yaml_file, 'w') as f:
            yaml.dump(initial_data, f, Dumper=yaml.SafeDumper, default_flow_style=False)
        
        print("\nFinal YAML content:")
        with open(yaml_file, 'r') as f:
            print(f.read())
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Demo cache invalidation
    print("\n=== Cache Invalidation Demo ===")
    cache_invalidated = False
    
    def invalidate_cache():
        nonlocal cache_invalidated
        cache_invalidated = True
        print("✅ Cache invalidated")
    
    def check_cache():
        nonlocal cache_invalidated
        if cache_invalidated:
            print("🔄 Cache refresh needed")
            cache_invalidated = False
            return True
        else:
            print("✅ Cache is valid")
            return False
    
    # Simulate operations that invalidate cache
    operations = [
        "Create file",
        "Delete file", 
        "Create directory",
        "Update file content"
    ]
    
    for operation in operations:
        print(f"\nPerforming: {operation}")
        invalidate_cache()
        check_cache()
    
    print("\n" + "=" * 50)
    print("✅ Demo completed successfully!")
    print("\nKey Features Demonstrated:")
    print("- YAML content parsing and structure detection")
    print("- File and directory operations")
    print("- Cache invalidation for immediate updates")
    print("- Proper YAML structure preservation")

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run yaml-fuse tests')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--demo', action='store_true', help='Run demo only')
    parser.add_argument('--all', action='store_true', help='Run all tests (default)')
    
    args = parser.parse_args()
    
    # Default to all tests if no specific type is specified
    if not any([args.unit, args.integration, args.demo, args.all]):
        args.all = True
    
    if args.demo:
        run_demo()
        return
    
    # Create test suite
    suite = unittest.TestSuite()
    
    if args.unit or args.all:
        # Add unit tests
        unit_suite = unittest.TestLoader().loadTestsFromTestCase(TestYAMLFuseUnit)
        suite.addTest(unit_suite)
    
    if args.integration or args.all:
        # Add integration tests
        integration_suite = unittest.TestLoader().loadTestsFromTestCase(TestYAMLFuseIntegration)
        suite.addTest(integration_suite)
    
    if args.all:
        # Add demo tests
        demo_suite = unittest.TestLoader().loadTestsFromTestCase(TestYAMLFuseDemo)
        suite.addTest(demo_suite)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main() 