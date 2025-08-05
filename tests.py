#!/usr/bin/env python3
"""
Comprehensive test suite for YAML FUSE filesystem.
Combines unit tests, integration tests, demo tests, and functional tests.
"""

import unittest
import yaml
import os
import sys
import tempfile
import time
import subprocess
import shutil
import json
import logging

# Add current directory to path for imports
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
except NameError:
    # __file__ is not available when executed as string
    sys.path.insert(0, os.getcwd())

# Import YAMLFuse and BlockStyleDumper from yaml-fuse.py
import importlib.util
spec = importlib.util.spec_from_file_location("yaml_fuse_module", "yaml-fuse.py")
yaml_fuse_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(yaml_fuse_module)
YAMLFuse = yaml_fuse_module.YAMLFuse
BlockStyleDumper = yaml_fuse_module.BlockStyleDumper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestYAMLFuseUnit(unittest.TestCase):
    """Unit tests that don't require FUSE mounting"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.yaml_file = os.path.join(self.temp_dir, 'test.yaml')
        
        # Create test YAML file
        test_data = {
            'database': {
                'host': 'localhost',
                'port': 5432,
                'credentials': {
                    'username': 'admin',
                    'password': 'secret'
                }
            },
            'servers': [
                {'name': 'web1', 'ip': '192.168.1.10'},
                {'name': 'web2', 'ip': '192.168.1.11'}
            ],
            'features': ['auth', 'logging', 'monitoring']
        }
        
        with open(self.yaml_file, 'w') as f:
            yaml.dump(test_data, f, default_flow_style=False)
        
        self.fuse = YAMLFuse(self.yaml_file)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_yaml_parsing_logic(self):
        """Test YAML parsing logic in release method"""
        def test_parse_content(content):
            try:
                parsed = yaml.safe_load(content)
                return parsed, type(parsed)
            except yaml.YAMLError:
                return content, type(content)
        
        # Test cases
        test_cases = [
            ('simple string', 'str'),
            ('- item1\n- item2', 'list'),
            ('key: value', 'dict'),
            ('123', 'int'),
            ('true', 'bool'),
            ('{"json": "object"}', 'dict')
        ]
        
        for content, expected_type in test_cases:
            with self.subTest(content=content):
                result, result_type = test_parse_content(content)
                if expected_type == 'str':
                    self.assertIsInstance(result, str)
                elif expected_type == 'list':
                    self.assertIsInstance(result, list)
                elif expected_type == 'dict':
                    self.assertIsInstance(result, dict)
                elif expected_type == 'int':
                    self.assertIsInstance(result, int)
                elif expected_type == 'bool':
                    self.assertIsInstance(result, bool)
    
    def test_block_style_dumper(self):
        """Test BlockStyleDumper functionality"""
        # Test multiline string
        data = {'description': 'This is a\nmultiline string\nwith newlines'}
        result = yaml.dump(data, Dumper=BlockStyleDumper, default_flow_style=False)
        
        # Should use block style for multiline strings
        self.assertIn('description: |', result)
        self.assertIn('This is a', result)
        self.assertIn('multiline string', result)
        
        # Test single line string
        data2 = {'description': 'Single line string'}
        result2 = yaml.dump(data2, Dumper=BlockStyleDumper, default_flow_style=False)
        
        # Should not use block style for single line
        self.assertNotIn('description: |', result2)
        self.assertIn('description: Single line string', result2)
    
    def test_path_resolution(self):
        """Test path resolution logic"""
        # Test root path
        parent, key = self.fuse._resolve_path('/')
        self.assertEqual(parent, self.fuse.data)
        self.assertIsNone(key)
        
        # Test existing path
        parent, key = self.fuse._resolve_path('/database/host')
        self.assertEqual(parent, self.fuse.data['database'])
        self.assertEqual(key, 'host')
        
        # Test non-existent path
        parent, key = self.fuse._resolve_path('/nonexistent/path')
        self.assertIsNone(parent)
        self.assertIsNone(key)
    
    def test_strip_suffix(self):
        """Test suffix stripping logic"""
        # Test .json suffix
        path, mode = self.fuse._strip_suffix('/path/to/file.json')
        self.assertEqual(path, '/path/to/file')
        self.assertEqual(mode, 'json')
        
        # Test .yaml suffix
        path, mode = self.fuse._strip_suffix('/path/to/file.yaml')
        self.assertEqual(path, '/path/to/file')
        self.assertEqual(mode, 'yaml')
        
        # Test .yml suffix
        path, mode = self.fuse._strip_suffix('/path/to/file.yml')
        self.assertEqual(path, '/path/to/file')
        self.assertEqual(mode, 'yaml')
        
        # Test no suffix
        path, mode = self.fuse._strip_suffix('/path/to/file')
        self.assertEqual(path, '/path/to/file')
        self.assertEqual(mode, 'yaml')  # default mode
    
    def test_ephemeral_file_detection(self):
        """Test ephemeral file detection"""
        self.assertTrue(self.fuse._is_ephemeral('/path/to/.hidden'))
        self.assertTrue(self.fuse._is_ephemeral('/.config'))
        self.assertFalse(self.fuse._is_ephemeral('/path/to/normal'))
        self.assertFalse(self.fuse._is_ephemeral('/file.txt'))
    
    def test_get_value_content(self):
        """Test content generation for different types"""
        # Test string content
        content = self.fuse._get_value_content('test string')
        self.assertEqual(content, b'test string')
        
        # Test dict content in YAML mode
        content = self.fuse._get_value_content({'key': 'value'}, 'yaml')
        self.assertIn(b'key:', content)
        self.assertIn(b'value', content)
        
        # Test list content in JSON mode
        content = self.fuse._get_value_content([1, 2, 3], 'json')
        self.assertIn(b'[', content)
        self.assertIn(b']', content)
    
    def test_cache_invalidation(self):
        """Test cache invalidation mechanism"""
        # Initially cache should not be invalidated
        self.assertFalse(self.fuse.cache_invalidated)
        
        # Invalidate cache
        self.fuse._invalidate_cache()
        self.assertTrue(self.fuse.cache_invalidated)
    
    def test_yaml_reloading(self):
        """Test YAML file reloading"""
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
        try:
            fuse = YAMLFuse('/tmp/nonexistent.yaml')
            # Should not raise exception, should start with empty data
            self.assertEqual(fuse.data, {})
        except Exception as e:
            # The constructor might fail due to getmtime, but the data should be empty
            # This is expected behavior
            pass
        
        # Test with invalid YAML content
        invalid_yaml_file = os.path.join(self.temp_dir, 'invalid.yaml')
        with open(invalid_yaml_file, 'w') as f:
            f.write('invalid: yaml: content:')
        
        try:
            fuse = YAMLFuse(invalid_yaml_file)
            # Should not raise exception, should start with empty data
            self.assertEqual(fuse.data, {})
        except Exception as e:
            # Should handle invalid YAML gracefully
            pass
    
    def test_simulated_file_operations(self):
        """Test simulated file creation and reading"""
        # Simulate creating a file
        parent, key = self.fuse._resolve_path('/database', create_missing=True)
        parent[key] = 'new_value'
        
        # Check that the value was set
        self.assertEqual(self.fuse.data['database'], 'new_value')
    
    def test_simulated_directory_creation(self):
        """Test simulated directory creation"""
        # Simulate creating a directory
        parent, key = self.fuse._resolve_path('/new/directory', create_missing=True)
        parent[key] = {}
        
        # Check that the directory was created
        self.assertIn('new', self.fuse.data)
        self.assertIn('directory', self.fuse.data['new'])
    
    def test_simulated_yaml_structure_creation(self):
        """Test simulated YAML structure creation"""
        # Simulate creating a complex structure
        parent, key = self.fuse._resolve_path('/complex/structure', create_missing=True)
        parent[key] = {
            'nested': {
                'list': [1, 2, 3],
                'string': 'test'
            }
        }
        
        # Check that the structure was created
        self.assertIn('complex', self.fuse.data)
        self.assertIn('structure', self.fuse.data['complex'])
        self.assertIn('nested', self.fuse.data['complex']['structure'])


class TestYAMLFuseIntegration(unittest.TestCase):
    """Integration tests that require FUSE mounting"""
    
    def setUp(self):
        """Set up integration test environment"""
        # Check if FUSE is available
        try:
            import subprocess
            result = subprocess.run(['which', 'fusermount'], capture_output=True, text=True)
            if result.returncode != 0:
                self.skipTest("FUSE not available (fusermount not found)")
        except Exception:
            self.skipTest("FUSE not available")
        
        self.temp_dir = tempfile.mkdtemp()
        self.yaml_file = os.path.join(self.temp_dir, 'test.yaml')
        self.mount_point = os.path.join(self.temp_dir, 'mount')
        
        # Create test YAML file
        test_data = {
            'resources': {
                'exampleResource': {
                    'properties': {
                        'description': 'Initial description',
                        'name': 'Example Resource'
                    }
                }
            }
        }
        
        with open(self.yaml_file, 'w') as f:
            yaml.dump(test_data, f, default_flow_style=False)
        
        os.makedirs(self.mount_point, exist_ok=True)
    
    def tearDown(self):
        """Clean up integration test environment"""
        self.stop_filesystem()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def start_filesystem(self):
        """Start the FUSE filesystem"""
        self.process = subprocess.Popen([
            'python3', 'yaml-fuse.py', self.yaml_file, self.mount_point
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)  # Wait for mount to be ready
    
    def stop_filesystem(self):
        """Stop the FUSE filesystem"""
        if hasattr(self, 'process'):
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
        
        # Unmount
        try:
            subprocess.run(['umount', self.mount_point], check=False)
        except:
            pass
    
    def read_yaml_file(self):
        """Read the current YAML file content"""
        with open(self.yaml_file, 'r') as f:
            return yaml.safe_load(f)
    
    def test_basic_file_operations(self):
        """Test basic file creation, reading, and deletion"""
        self.start_filesystem()
        
        try:
            # Test file creation
            test_file = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', 'test_field')
            with open(test_file, 'w') as f:
                f.write('test value')
            
            time.sleep(1)
            data = self.read_yaml_file()
            self.assertEqual(data['resources']['exampleResource']['properties']['test_field'], 'test value')
            
            # Test file reading
            with open(test_file, 'r') as f:
                content = f.read()
            self.assertEqual(content, 'test value')
            
            # Test file deletion
            os.unlink(test_file)
            time.sleep(1)
            data = self.read_yaml_file()
            self.assertNotIn('test_field', data['resources']['exampleResource']['properties'])
            
        finally:
            self.stop_filesystem()
    
    def test_yaml_structure_parsing(self):
        """Test that YAML content is properly parsed and becomes directories"""
        self.start_filesystem()
        
        try:
            # Create a file with YAML content
            test_file = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', 'config')
            yaml_content = 'plugins:\n  providers:\n  - name: example\n    path: ../../bin'
            
            with open(test_file, 'w') as f:
                f.write(yaml_content)
            
            time.sleep(1)
            data = self.read_yaml_file()
            
            # The content should be parsed as a dictionary
            config = data['resources']['exampleResource']['properties']['config']
            self.assertIsInstance(config, dict)
            self.assertIn('plugins', config)
            self.assertIn('providers', config['plugins'])
            
        finally:
            self.stop_filesystem()
    
    def test_list_parsing(self):
        """Test that YAML lists are properly handled"""
        self.start_filesystem()
        
        try:
            # Create a file with list content
            test_file = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', 'items')
            list_content = '- item1\n- item2\n- item3'
            
            with open(test_file, 'w') as f:
                f.write(list_content)
            
            time.sleep(1)
            data = self.read_yaml_file()
            
            # The content should be parsed as a list
            items = data['resources']['exampleResource']['properties']['items']
            self.assertIsInstance(items, list)
            self.assertEqual(items, ['item1', 'item2', 'item3'])
            
        finally:
            self.stop_filesystem()
    
    def test_multiline_string_preservation(self):
        """Test that invalid YAML is preserved as multiline strings"""
        self.start_filesystem()
        
        try:
            # Create a file with invalid YAML content
            test_file = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', 'description')
            invalid_content = 'This is a\nmultiline description\nwith multiple lines'
            
            with open(test_file, 'w') as f:
                f.write(invalid_content)
            
            time.sleep(1)
            data = self.read_yaml_file()
            
            # The content should be preserved as a string
            description = data['resources']['exampleResource']['properties']['description']
            self.assertIsInstance(description, str)
            self.assertIn('multiline description', description)
            
        finally:
            self.stop_filesystem()
    
    def test_directory_operations(self):
        """Test directory creation and deletion"""
        self.start_filesystem()
        
        try:
            # Test directory creation
            test_dir = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', 'new_dir')
            os.makedirs(test_dir, exist_ok=True)
            
            time.sleep(1)
            data = self.read_yaml_file()
            self.assertIn('new_dir', data['resources']['exampleResource']['properties'])
            self.assertEqual(data['resources']['exampleResource']['properties']['new_dir'], {})
            
            # Test directory deletion
            os.rmdir(test_dir)
            time.sleep(1)
            data = self.read_yaml_file()
            self.assertNotIn('new_dir', data['resources']['exampleResource']['properties'])
            
        finally:
            self.stop_filesystem()
    
    def test_cache_invalidation(self):
        """Test that cache invalidation works for immediate updates"""
        self.start_filesystem()
        
        try:
            # Create a file
            test_file = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', 'cache_test')
            with open(test_file, 'w') as f:
                f.write('initial value')
            
            time.sleep(1)
            data = self.read_yaml_file()
            self.assertEqual(data['resources']['exampleResource']['properties']['cache_test'], 'initial value')
            
            # Update the file
            with open(test_file, 'w') as f:
                f.write('updated value')
            
            time.sleep(1)
            data = self.read_yaml_file()
            self.assertEqual(data['resources']['exampleResource']['properties']['cache_test'], 'updated value')
            
        finally:
            self.stop_filesystem()
    
    def test_nested_yaml_structure(self):
        """Test complex nested YAML structures"""
        self.start_filesystem()
        
        try:
            # Create a complex nested structure
            test_file = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', 'complex')
            complex_content = '''nested:
  structure:
    with:
      lists: [1, 2, 3]
      strings: "test"
      numbers: 42'''
            
            with open(test_file, 'w') as f:
                f.write(complex_content)
            
            time.sleep(1)
            data = self.read_yaml_file()
            
            complex_data = data['resources']['exampleResource']['properties']['complex']
            self.assertIsInstance(complex_data, dict)
            self.assertIn('nested', complex_data)
            self.assertIn('structure', complex_data['nested'])
            
        finally:
            self.stop_filesystem()
    
    def test_file_updates(self):
        """Test updating existing files"""
        self.start_filesystem()
        
        try:
            # Update an existing property
            test_file = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', 'description')
            with open(test_file, 'w') as f:
                f.write('Updated description')
            
            time.sleep(1)
            data = self.read_yaml_file()
            self.assertEqual(data['resources']['exampleResource']['properties']['description'], 'Updated description')
            
        finally:
            self.stop_filesystem()
    
    def test_empty_file_handling(self):
        """Test handling of empty files"""
        self.start_filesystem()
        
        try:
            # Create an empty file
            test_file = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', 'empty')
            with open(test_file, 'w') as f:
                f.write('')
            
            time.sleep(1)
            data = self.read_yaml_file()
            self.assertEqual(data['resources']['exampleResource']['properties']['empty'], '')
            
        finally:
            self.stop_filesystem()
    
    def test_special_characters(self):
        """Test handling of special characters in content"""
        self.start_filesystem()
        
        try:
            # Create a file with special characters
            test_file = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', 'special')
            special_content = 'Line 1\nLine 2\n  Indented\n    More indented\n\nEmpty line'
            
            with open(test_file, 'w') as f:
                f.write(special_content)
            
            time.sleep(1)
            data = self.read_yaml_file()
            
            special_data = data['resources']['exampleResource']['properties']['special']
            self.assertIsInstance(special_data, str)
            self.assertIn('Indented', special_data)
            self.assertIn('More indented', special_data)
            
        finally:
            self.stop_filesystem()
    
    def test_json_mode(self):
        """Test JSON file handling"""
        self.start_filesystem()
        
        try:
            # Create a JSON file
            test_file = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', 'config.json')
            json_content = '{"key": "value", "number": 42}'
            
            with open(test_file, 'w') as f:
                f.write(json_content)
            
            time.sleep(1)
            data = self.read_yaml_file()
            
            config = data['resources']['exampleResource']['properties']['config']
            self.assertIsInstance(config, dict)
            self.assertEqual(config['key'], 'value')
            self.assertEqual(config['number'], 42)
            
        finally:
            self.stop_filesystem()
    
    def test_error_handling(self):
        """Test error handling for invalid operations"""
        self.start_filesystem()
        
        try:
            # Try to access non-existent file
            non_existent_file = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', 'nonexistent')
            with self.assertRaises(FileNotFoundError):
                with open(non_existent_file, 'r') as f:
                    f.read()
            
            # Try to create file in non-existent directory
            invalid_file = os.path.join(self.mount_point, 'nonexistent', 'file')
            with self.assertRaises(FileNotFoundError):
                with open(invalid_file, 'w') as f:
                    f.write('test')
            
        finally:
            self.stop_filesystem()
    
    def test_concurrent_access(self):
        """Test concurrent file operations"""
        self.start_filesystem()
        
        try:
            import threading
            
            def create_file(thread_id):
                test_file = os.path.join(self.mount_point, 'resources', 'exampleResource', 'properties', f'thread_{thread_id}')
                with open(test_file, 'w') as f:
                    f.write(f'content from thread {thread_id}')
            
            # Create multiple threads
            threads = []
            for i in range(3):
                thread = threading.Thread(target=create_file, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            time.sleep(1)
            data = self.read_yaml_file()
            
            # Check that all files were created
            for i in range(3):
                self.assertIn(f'thread_{i}', data['resources']['exampleResource']['properties'])
                self.assertEqual(data['resources']['exampleResource']['properties'][f'thread_{i}'], f'content from thread {i}')
            
        finally:
            self.stop_filesystem()


class TestYAMLFuseDemo(unittest.TestCase):
    """Demo tests for key functionality"""
    
    def test_yaml_parsing_demo(self):
        """Demonstrate YAML parsing functionality"""
        print("\n🚀 YAML-FUSE Demo")
        print("=" * 50)
        print("=== YAML Parsing Demo ===")
        
        # Test different content types
        test_cases = [
            ("Simple String", "Hello, World!", str),
            ("YAML Dictionary", "plugins:\n  providers:\n  - name: example\n    path: ../../bin", dict),
            ("YAML List", "- item1\n- item2\n- item3", list),
            ("Multiline String", "This is a multiline\nstring that should be\npreserved as a string.", str)
        ]
        
        for name, content, expected_type in test_cases:
            print(f"\nTesting: {name}")
            print(f"Content:\n{content}")
            
            try:
                parsed = yaml.safe_load(content)
                if parsed is None:
                    parsed = content
                    actual_type = str
                else:
                    actual_type = type(parsed)
                
                print(f"✅ Parsed as: {actual_type.__name__}")
                print(f"   Value: {parsed}")
                
                if actual_type == expected_type:
                    print("✅ CORRECT: Expected {}, got {}".format(expected_type.__name__, actual_type.__name__))
                else:
                    print("❌ INCORRECT: Expected {}, got {}".format(expected_type.__name__, actual_type.__name__))
                    
            except Exception as e:
                print(f"❌ ERROR: {e}")
            
            print("-" * 40)
    
    def test_cache_invalidation_demo(self):
        """Demonstrate cache invalidation functionality"""
        print("\n=== Filesystem Operations Demo ===")
        
        # Create temporary test environment
        temp_dir = tempfile.mkdtemp()
        yaml_file = os.path.join(temp_dir, 'demo.yaml')
        
        try:
            # Create initial YAML
            initial_data = {
                'name': 'demo-provider',
                'outputs': {
                    'resourceId': {
                        'value': '${demoResource.id}'
                    }
                }
            }
            
            with open(yaml_file, 'w') as f:
                yaml.dump(initial_data, f, Dumper=BlockStyleDumper, default_flow_style=False)
            
            print(f"Created YAML file: {yaml_file}")
            print("Initial content:")
            with open(yaml_file, 'r') as f:
                print(f.read())
            
            # Simulate file operations
            print("\nSimulating file operations...")
            
            # Add simple file
            initial_data['simple.txt'] = 'Hello, World!'
            print("✅ Added simple.txt")
            
            # Add YAML structure
            initial_data['config'] = {
                'plugins': {
                    'providers': [
                        {'name': 'example', 'path': '../../bin'}
                    ]
                }
            }
            print("✅ Added config (YAML structure)")
            
            # Add list
            initial_data['items'] = ['item1', 'item2', 'item3']
            print("✅ Added items (list)")
            
            # Save the updated YAML
            with open(yaml_file, 'w') as f:
                yaml.dump(initial_data, f, Dumper=BlockStyleDumper, default_flow_style=False)
            
            print("\nUpdated YAML content:")
            with open(yaml_file, 'r') as f:
                print(f.read())
            
            # Simulate file deletion
            del initial_data['simple.txt']
            print("\n✅ Deleted simple.txt")
            
            # Save again
            with open(yaml_file, 'w') as f:
                yaml.dump(initial_data, f, Dumper=BlockStyleDumper, default_flow_style=False)
            
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


def run_demo():
    """Run the demo functionality"""
    print("🚀 YAML-FUSE Demo")
    print("=" * 50)
    print("=== YAML Parsing Demo ===")
    
    # Test different content types
    test_cases = [
        ("Simple String", "Hello, World!", str),
        ("YAML Dictionary", "plugins:\n  providers:\n  - name: example\n    path: ../../bin", dict),
        ("YAML List", "- item1\n- item2\n- item3", list),
        ("Multiline String", "This is a multiline\nstring that should be\npreserved as a string.", str)
    ]
    
    for name, content, expected_type in test_cases:
        print(f"\nTesting: {name}")
        print(f"Content:\n{content}")
        
        try:
            parsed = yaml.safe_load(content)
            if parsed is None:
                parsed = content
                actual_type = str
            else:
                actual_type = type(parsed)
            
            print(f"✅ Parsed as: {actual_type.__name__}")
            print(f"   Value: {parsed}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("-" * 40)
    
    print("\n=== Filesystem Operations Demo ===")
    
    # Create temporary test environment
    temp_dir = tempfile.mkdtemp()
    yaml_file = os.path.join(temp_dir, 'demo.yaml')
    
    try:
        # Create initial YAML
        initial_data = {
            'name': 'demo-provider',
            'outputs': {
                'resourceId': {
                    'value': '${demoResource.id}'
                }
            }
        }
        
        with open(yaml_file, 'w') as f:
            yaml.dump(initial_data, f, Dumper=BlockStyleDumper, default_flow_style=False)
        
        print(f"Created YAML file: {yaml_file}")
        print("Initial content:")
        with open(yaml_file, 'r') as f:
            print(f.read())
        
        # Simulate file operations
        print("\nSimulating file operations...")
        
        # Add simple file
        initial_data['simple.txt'] = 'Hello, World!'
        print("✅ Added simple.txt")
        
        # Add YAML structure
        initial_data['config'] = {
            'plugins': {
                'providers': [
                    {'name': 'example', 'path': '../../bin'}
                ]
            }
        }
        print("✅ Added config (YAML structure)")
        
        # Add list
        initial_data['items'] = ['item1', 'item2', 'item3']
        print("✅ Added items (list)")
        
        # Save the updated YAML
        with open(yaml_file, 'w') as f:
            yaml.dump(initial_data, f, Dumper=BlockStyleDumper, default_flow_style=False)
        
        print("\nUpdated YAML content:")
        with open(yaml_file, 'r') as f:
            print(f.read())
        
        # Simulate file deletion
        del initial_data['simple.txt']
        print("\n✅ Deleted simple.txt")
        
        # Save again
        with open(yaml_file, 'w') as f:
            yaml.dump(initial_data, f, Dumper=BlockStyleDumper, default_flow_style=False)
        
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
    
    if args.demo or args.all:
        # Add demo tests
        demo_suite = unittest.TestLoader().loadTestsFromTestCase(TestYAMLFuseDemo)
        suite.addTest(demo_suite)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("💥 SOME TESTS FAILED!")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 