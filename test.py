#!/usr/bin/env python3
"""
Comprehensive test suite for YAML FUSE tool

This single test file covers all functionality:
- Block style YAML saving
- FUSE write operations  
- String parsing and preservation
- Direct YAML functionality
- List parsing
- Multiline string preservation
- Single-line string handling
- YAML structure detection
"""

import yaml
import tempfile
import os
import subprocess
import time

# Custom dumper that forces block style for multiline strings
class BlockStyleDumper(yaml.SafeDumper):
    def represent_scalar(self, tag, value, style=None):
        """Override scalar representation to force block style for multiline strings"""
        if tag == 'tag:yaml.org,2002:str':
            # Check if this is actually a multiline string (has multiple lines)
            # Strip trailing newlines to avoid counting them as extra lines
            stripped = value.rstrip('\n')
            if '\n' in stripped and len(stripped.split('\n')) > 1:
                return super().represent_scalar(tag, value, style='|')
        return super().represent_scalar(tag, value, style)
    
    def represent_sequence(self, tag, sequence, flow_style=None):
        """Force block style for lists"""
        return super().represent_sequence(tag, sequence, flow_style=False)

def test_block_style_saving():
    """Test that multiline strings are saved as block style"""
    print("=" * 60)
    print("TEST 1: Block Style YAML Saving")
    print("=" * 60)
    
    # Test data with multiline strings
    test_data = {
        'single_line': 'This is a single line string',
        'multiline_string': 'Line 1\nLine 2\nLine 3',
        'multiline_with_spaces': '  Line 1  \n  Line 2  \n  Line 3  ',
        'list_example': ['item1', 'item2', 'item3'],
        'mixed_content': {
            'description': 'This is a\nmultiline description\nwith multiple lines',
            'config': 'single line config'
        }
    }
    
    # Save using BlockStyleDumper
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_data, f, Dumper=BlockStyleDumper, default_flow_style=False, 
                  sort_keys=False, width=float("inf"), allow_unicode=True, 
                  explicit_end=False)
        temp_file = f.name
    
    # Read back and check the content
    with open(temp_file, 'r') as f:
        content = f.read()
    
    print("Generated YAML content:")
    print("-" * 40)
    print(content)
    print("-" * 40)
    
    # Check if multiline strings are in block style
    lines = content.split('\n')
    block_style_found = False
    
    for i, line in enumerate(lines):
        if 'multiline_string: |' in line:
            print(f"✓ Found block style for multiline_string at line {i+1}")
            block_style_found = True
        elif 'description: |' in line:
            print(f"✓ Found block style for description at line {i+1}")
            block_style_found = True
    
    if not block_style_found:
        print("✗ No block style found for multiline strings!")
        return False
    
    # Verify single-line strings are NOT in block style
    single_line_block_found = False
    for i, line in enumerate(lines):
        if 'single_line: |' in line:
            print(f"✗ Single line string incorrectly in block style at line {i+1}")
            single_line_block_found = True
        elif 'config: |' in line:
            print(f"✗ Single line config incorrectly in block style at line {i+1}")
            single_line_block_found = True
    
    if single_line_block_found:
        print("✗ Single line strings incorrectly saved as block style!")
        return False
    
    print("✓ Block style saving test passed!")
    return True

def test_direct_yaml_save():
    """Test direct YAML saving functionality"""
    print("\n" + "=" * 60)
    print("TEST 2: Direct YAML Save")
    print("=" * 60)
    
    # Test data similar to what the user wants
    test_data = {
        'resources': {
            'example_resource': {
                'properties': {
                    'description': 'Initial description',
                    'test_field': 'a\n- b'  # This should be saved as block style
                }
            }
        }
    }
    
    print("Test data:")
    print(f"test_field value: {repr(test_data['resources']['example_resource']['properties']['test_field'])}")
    print("Contains newlines:", '\n' in test_data['resources']['example_resource']['properties']['test_field'])
    
    # Save using our custom dumper
    result = yaml.dump(test_data, Dumper=BlockStyleDumper, default_flow_style=False)
    
    print("\nGenerated YAML:")
    print("-" * 40)
    print(result)
    print("-" * 40)
    
    # Check if test_field is saved as block style
    if 'test_field: |' in result:
        print("✅ SUCCESS: test_field saved as block style")
        return True
    else:
        print("❌ FAILURE: test_field not saved as block style")
        return False

def test_string_parsing():
    """Test string parsing behavior"""
    print("\n" + "=" * 60)
    print("TEST 3: String Parsing")
    print("=" * 60)
    
    # Test the content that's actually being written
    test_content = "a\n- b\n"  # This is what echo "a\n- b" actually writes
    user_content = "a\n- b"    # No trailing newline
    
    print(f"Test content: {repr(test_content)}")
    print("Contains newlines:", '\n' in test_content)
    
    # Try to parse as YAML
    try:
        parsed = yaml.safe_load(test_content)
        print(f"Parsed as YAML: {parsed}")
        print(f"Type: {type(parsed)}")
    except yaml.YAMLError as e:
        print(f"Not valid YAML: {e}")
    
    print(f"\nUser content: {repr(user_content)}")
    
    try:
        parsed = yaml.safe_load(user_content)
        print(f"Parsed as YAML: {parsed}")
        print(f"Type: {type(parsed)}")
    except yaml.YAMLError as e:
        print(f"Not valid YAML: {e}")
    
    print("✓ String parsing test completed!")
    return True

def test_fuse_write():
    """Test writing to FUSE filesystem"""
    print("\n" + "=" * 60)
    print("TEST 4: FUSE Write Operations")
    print("=" * 60)
    
    # Create mount point
    mount_point = "/tmp/test_fuse_mount"
    yaml_file = "test_fuse.yaml"
    
    # Create a simple YAML file
    test_data = {
        'resources': {
            'example_resource': {
                'properties': {
                    'description': 'Initial description'
                }
            }
        }
    }
    
    with open(yaml_file, 'w') as f:
        yaml.dump(test_data, f)
    
    print(f"Created test YAML file: {yaml_file}")
    
    # Start FUSE mount
    try:
        # Create mount point
        os.makedirs(mount_point, exist_ok=True)
        
        # Start FUSE in background
        process = subprocess.Popen([
            'python3', 'yaml-fuse.py', yaml_file, mount_point
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for mount to be ready
        time.sleep(3)
        
        # Check if mount is working
        if not os.path.exists(f"{mount_point}/resources"):
            print("❌ FUSE mount not working")
            return False
        
        print("✅ FUSE mount is working")
        
        # Write multiline string to FUSE
        test_content = "a\n- b"
        target_file = f"{mount_point}/resources/example_resource/properties/test_field"
        
        with open(target_file, 'w') as f:
            f.write(test_content)
        
        print(f"✅ Wrote content to FUSE file: {repr(test_content)}")
        
        # Wait a moment for the file to be saved
        time.sleep(2)
        
        # Check the YAML file
        with open(yaml_file, 'r') as f:
            updated_data = yaml.safe_load(f)
        
        print(f"Updated YAML data: {updated_data}")
        
        # Check if test_field exists and is a string
        test_field_value = updated_data.get('resources', {}).get('example_resource', {}).get('properties', {}).get('test_field')
        
        if test_field_value is None:
            print("❌ test_field not found in YAML")
            return False
        
        print(f"test_field value: {repr(test_field_value)}")
        
        # Check if it's a string (which is correct for 'a\n- b' since it's not valid YAML)
        if isinstance(test_field_value, str):
            print("✅ test_field is a string (correct for invalid YAML)")
            
            # Check the YAML file content to see if it's in block style
            with open(yaml_file, 'r') as f:
                yaml_content = f.read()
            
            print("YAML file content:")
            print("-" * 40)
            print(yaml_content)
            print("-" * 40)
            
            # For 'a\n- b', it should be saved as a multiline string in block style
            # because it doesn't start with '-' so it's treated as a string
            if 'test_field: |' in yaml_content:
                print("✅ test_field saved correctly as multiline string in YAML")
                return True
            else:
                print("❌ test_field not saved correctly in YAML")
                return False
        else:
            print("❌ test_field is not a string")
            return False
        
    finally:
        # Cleanup
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
        
        # Unmount
        try:
            subprocess.run(['umount', mount_point], check=False)
        except:
            pass
        
        # Clean up files
        try:
            os.remove(yaml_file)
            os.rmdir(mount_point)
        except:
            pass

def test_simple_block_style():
    """Test the basic case that the user mentioned"""
    print("\n" + "=" * 60)
    print("TEST 5: Simple Block Style Test")
    print("=" * 60)
    
    # Test the basic case that the user mentioned
    test_data = {
        'test_field': 'a\n- b'  # This should be a multiline string
    }
    
    print("Test data:", test_data)
    print("String contains newlines:", '\n' in test_data['test_field'])
    
    # Save using our custom dumper
    result = yaml.dump(test_data, Dumper=BlockStyleDumper, default_flow_style=False)
    print("\nGenerated YAML:")
    print("-" * 40)
    print(result)
    print("-" * 40)
    
    # Check if it's in block style
    if 'test_field: |' in result:
        print("✅ SUCCESS: String saved as block style")
        return True
    else:
        print("❌ FAILURE: String not saved as block style")
        return False

def test_list_parsing():
    """Test that YAML lists are parsed correctly"""
    print("\n" + "=" * 60)
    print("TEST 6: List Parsing")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        # (input, expected_type, description)
        ('- a\n- b', list, 'Simple YAML list'),
        ('- item1\n- item2\n- item3', list, 'Multi-item YAML list'),
        ('a\n- b', str, 'Invalid YAML (first item not prefixed with -)'),
        ('This is a\nmultiline string', str, 'Multiline string'),
        ('Single line string', str, 'Single line string'),
        ('123', int, 'Number'),
        ('true', bool, 'Boolean'),
        ('{"key": "value"}', dict, 'JSON object'),
    ]
    
    print("Testing YAML parsing logic:")
    print("=" * 50)
    
    for i, (input_content, expected_type, description) in enumerate(test_cases, 1):
        print(f"\nTest {i}: {description}")
        print(f"Input: {repr(input_content)}")
        
        # Simulate the FUSE logic
        try:
            parsed_yaml = yaml.safe_load(input_content)
            actual_type = type(parsed_yaml)
            print(f"Parsed as: {parsed_yaml} (type: {actual_type.__name__})")
            
            if actual_type == expected_type:
                print(f"✅ CORRECT: Expected {expected_type.__name__}, got {actual_type.__name__}")
            else:
                print(f"❌ WRONG: Expected {expected_type.__name__}, got {actual_type.__name__}")
                
        except yaml.YAMLError as e:
            print(f"YAML Error: {e}")
            if expected_type == str:
                print(f"✅ CORRECT: Invalid YAML treated as string")
            else:
                print(f"❌ WRONG: Expected {expected_type.__name__}, but got YAML error")
    
    print("\n" + "=" * 50)
    print("Testing specific user case:")
    
    # Test the user's specific case
    user_input = '- a\n- b'
    print(f"User input: {repr(user_input)}")
    
    try:
        parsed = yaml.safe_load(user_input)
        print(f"Parsed result: {parsed}")
        print(f"Type: {type(parsed).__name__}")
        
        if isinstance(parsed, list):
            print("✅ SUCCESS: Correctly parsed as YAML list")
            
            # Test saving with our custom dumper
            test_data = {'test_field': parsed}
            result = yaml.dump(test_data, default_flow_style=False)
            print(f"\nSaved YAML:\n{result}")
            
            if '- a' in result and '- b' in result:
                print("✅ SUCCESS: List saved correctly in YAML")
                return True
            else:
                print("❌ FAILURE: List not saved correctly")
                return False
        else:
            print("❌ FAILURE: Should be parsed as list")
            return False
            
    except yaml.YAMLError as e:
        print(f"❌ FAILURE: YAML parsing error: {e}")
        return False

def test_fuse_list_write():
    """Test writing YAML lists to FUSE filesystem"""
    print("\n" + "=" * 60)
    print("TEST 7: FUSE List Write")
    print("=" * 60)
    
    # Create mount point
    mount_point = "/tmp/test_fuse_list"
    yaml_file = "test_fuse_list.yaml"
    
    # Create a simple YAML file
    test_data = {
        'resources': {
            'example_resource': {
                'properties': {
                    'description': 'Initial description'
                }
            }
        }
    }
    
    with open(yaml_file, 'w') as f:
        yaml.dump(test_data, f)
    
    print(f"Created test YAML file: {yaml_file}")
    
    # Start FUSE mount
    try:
        # Create mount point
        os.makedirs(mount_point, exist_ok=True)
        
        # Start FUSE in background
        process = subprocess.Popen([
            'python3', 'yaml-fuse.py', yaml_file, mount_point
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for mount to be ready
        time.sleep(3)
        
        # Check if mount is working
        if not os.path.exists(f"{mount_point}/resources"):
            print("❌ FUSE mount not working")
            return False
        
        print("✅ FUSE mount is working")
        
        # Write YAML list to FUSE
        test_content = "- a\n- b"
        target_file = f"{mount_point}/resources/example_resource/properties/test_field"
        
        with open(target_file, 'w') as f:
            f.write(test_content)
        
        print(f"✅ Wrote content to FUSE file: {repr(test_content)}")
        
        # Wait a moment for the file to be saved
        time.sleep(2)
        
        # Check the YAML file
        with open(yaml_file, 'r') as f:
            updated_data = yaml.safe_load(f)
        
        print(f"Updated YAML data: {updated_data}")
        
        # Check if test_field exists and is a list
        test_field_value = updated_data.get('resources', {}).get('example_resource', {}).get('properties', {}).get('test_field')
        
        if test_field_value is None:
            print("❌ test_field not found in YAML")
            return False
        
        print(f"test_field value: {repr(test_field_value)}")
        print(f"test_field type: {type(test_field_value).__name__}")
        
        # Check if it's a list
        if isinstance(test_field_value, list):
            print("✅ test_field is a list")
            
            # Check the YAML file content to see if it's saved as a list
            with open(yaml_file, 'r') as f:
                yaml_content = f.read()
            
            print("YAML file content:")
            print("-" * 40)
            print(yaml_content)
            print("-" * 40)
            
            if '- a' in yaml_content and '- b' in yaml_content:
                print("✅ test_field saved as YAML list")
                return True
            else:
                print("❌ test_field not saved as YAML list")
                return False
        else:
            print("❌ test_field is not a list")
            return False
        
    finally:
        # Cleanup
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
        
        # Unmount
        try:
            subprocess.run(['umount', mount_point], check=False)
        except:
            pass
        
        # Clean up files
        try:
            os.remove(yaml_file)
            os.rmdir(mount_point)
        except:
            pass

def test_multiline_string_preservation():
    """Test that multiline strings are preserved correctly"""
    print("\n" + "=" * 60)
    print("TEST 8: Multiline String Preservation")
    print("=" * 60)
    
    # Create mount point
    mount_point = "/tmp/test_multiline"
    yaml_file = "test_multiline.yaml"
    
    # Create a simple YAML file
    test_data = {
        'resources': {
            'example_resource': {
                'properties': {
                    'description': 'Initial description'
                }
            }
        }
    }
    
    with open(yaml_file, 'w') as f:
        yaml.dump(test_data, f)
    
    print(f"Created test YAML file: {yaml_file}")
    
    # Start FUSE mount
    try:
        # Create mount point
        os.makedirs(mount_point, exist_ok=True)
        
        # Start FUSE in background
        process = subprocess.Popen([
            'python3', 'yaml-fuse.py', yaml_file, mount_point
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for mount to be ready
        time.sleep(3)
        
        # Check if mount is working
        if not os.path.exists(f"{mount_point}/resources"):
            print("❌ FUSE mount not working")
            return False
        
        print("✅ FUSE mount is working")
        
        # Write multiline string to description
        test_content = """This is a
multiline description
with multiple lines
  and some indentation
    and more indentation

And empty lines too!"""
        
        target_file = f"{mount_point}/resources/example_resource/properties/description"
        
        with open(target_file, 'w') as f:
            f.write(test_content)
        
        print(f"✅ Wrote multiline content to FUSE file")
        print(f"Content: {repr(test_content)}")
        
        # Wait a moment for the file to be saved
        time.sleep(2)
        
        # Check the YAML file
        with open(yaml_file, 'r') as f:
            updated_data = yaml.safe_load(f)
        
        print(f"Updated YAML data: {updated_data}")
        
        # Check if description field exists and is a string
        description_value = updated_data.get('resources', {}).get('example_resource', {}).get('properties', {}).get('description')
        
        if description_value is None:
            print("❌ description field not found in YAML")
            return False
        
        print(f"description value: {repr(description_value)}")
        print(f"description type: {type(description_value).__name__}")
        
        # Check if it's a string with newlines
        if isinstance(description_value, str) and '\n' in description_value:
            print("✅ description is a multiline string")
            
            # Check the YAML file content to see if it's in block style
            with open(yaml_file, 'r') as f:
                yaml_content = f.read()
            
            print("YAML file content:")
            print("-" * 40)
            print(yaml_content)
            print("-" * 40)
            
            if 'description: |' in yaml_content:
                print("✅ description saved as block style in YAML")
                return True
            else:
                print("❌ description not saved as block style in YAML")
                return False
        else:
            print("❌ description is not a multiline string")
            return False
        
    finally:
        # Cleanup
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
        
        # Unmount
        try:
            subprocess.run(['umount', mount_point], check=False)
        except:
            pass
        
        # Clean up files
        try:
            os.remove(yaml_file)
            os.rmdir(mount_point)
        except:
            pass

def test_both_functionality():
    """Test both multiline strings and YAML lists"""
    print("\n" + "=" * 60)
    print("TEST 9: Both Functionality")
    print("=" * 60)
    
    # Create mount point
    mount_point = "/tmp/test_both"
    yaml_file = "test_both.yaml"
    
    # Create a simple YAML file
    test_data = {
        'resources': {
            'example_resource': {
                'properties': {
                    'description': 'Initial description'
                }
            }
        }
    }
    
    with open(yaml_file, 'w') as f:
        yaml.dump(test_data, f)
    
    print(f"Created test YAML file: {yaml_file}")
    
    # Start FUSE mount
    try:
        # Create mount point
        os.makedirs(mount_point, exist_ok=True)
        
        # Start FUSE in background
        process = subprocess.Popen([
            'python3', 'yaml-fuse.py', yaml_file, mount_point
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for mount to be ready
        time.sleep(3)
        
        # Check if mount is working
        if not os.path.exists(f"{mount_point}/resources"):
            print("❌ FUSE mount not working")
            return False
        
        print("✅ FUSE mount is working")
        
        # Test 1: Write multiline string to description
        multiline_content = """This is a
multiline description
with multiple lines"""
        
        description_file = f"{mount_point}/resources/example_resource/properties/description"
        with open(description_file, 'w') as f:
            f.write(multiline_content)
        
        print(f"✅ Wrote multiline content to description")
        
        # Test 2: Write YAML list to test_field
        list_content = "- a\n- b"
        test_field_file = f"{mount_point}/resources/example_resource/properties/test_field"
        with open(test_field_file, 'w') as f:
            f.write(list_content)
        
        print(f"✅ Wrote list content to test_field")
        
        # Wait a moment for the files to be saved
        time.sleep(2)
        
        # Check the YAML file
        with open(yaml_file, 'r') as f:
            updated_data = yaml.safe_load(f)
        
        print(f"Updated YAML data: {updated_data}")
        
        # Check description (should be multiline string)
        description_value = updated_data.get('resources', {}).get('example_resource', {}).get('properties', {}).get('description')
        if isinstance(description_value, str) and '\n' in description_value:
            print("✅ description is a multiline string")
        else:
            print("❌ description is not a multiline string")
            return False
        
        # Check test_field (should be a list)
        test_field_value = updated_data.get('resources', {}).get('example_resource', {}).get('properties', {}).get('test_field')
        if isinstance(test_field_value, list):
            print("✅ test_field is a list")
        else:
            print("❌ test_field is not a list")
            return False
        
        # Check the YAML file content
        with open(yaml_file, 'r') as f:
            yaml_content = f.read()
        
        print("YAML file content:")
        print("-" * 40)
        print(yaml_content)
        print("-" * 40)
        
        # Verify both are saved correctly
        if 'description: |' in yaml_content and '- a' in yaml_content and '- b' in yaml_content:
            print("✅ Both multiline string and list saved correctly")
            return True
        else:
            print("❌ Not both saved correctly")
            return False
        
    finally:
        # Cleanup
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
        
        # Unmount
        try:
            subprocess.run(['umount', mount_point], check=False)
        except:
            pass
        
        # Clean up files
        try:
            os.remove(yaml_file)
            os.rmdir(mount_point)
        except:
            pass

def run_all_tests():
    """Run all tests and report results"""
    print("🧪 YAML FUSE COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Block Style YAML Saving", test_block_style_saving),
        ("Direct YAML Save", test_direct_yaml_save),
        ("String Parsing", test_string_parsing),
        ("FUSE Write Operations", test_fuse_write),
        ("Simple Block Style", test_simple_block_style),
        ("List Parsing", test_list_parsing),
        ("FUSE List Write", test_fuse_list_write),
        ("Multiline String Preservation", test_multiline_string_preservation),
        ("Both Functionality", test_both_functionality),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The YAML FUSE tool is working correctly.")
        return True
    else:
        print("💥 SOME TESTS FAILED! Please check the implementation.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1) 