#!/usr/bin/env python3
"""
Demo script for YAML FUSE filesystem

This script demonstrates the basic functionality of the YAML fuse tool.
"""

import os
import yaml
import subprocess
import time
import signal
import sys

def create_demo_yaml():
    """Create a demo YAML file"""
    demo_data = {
        'app': {
            'name': 'MyApp',
            'version': '1.0.0',
            'environment': 'production'
        },
        'database': {
            'host': 'db.example.com',
            'port': 5432,
            'name': 'myapp_db'
        },
        'features': [
            'authentication',
            'authorization',
            'logging'
        ],
        'settings': {
            'debug': False,
            'timeout': 30,
            'retries': 3
        },
        'applies_to': [
            'production',
            'staging',
            'development'
        ],
        'allowed_ips': [
            '192.168.1.0/24',
            '10.0.0.0/8',
            '172.16.0.0/12'
        ],
        'features': [
            'authentication',
            'authorization',
            'logging',
            'monitoring',
            'backup'
        ],
        'dependencies': [
            'nginx',
            'postgresql',
            'redis',
            'elasticsearch'
        ]
    }
    
    with open('demo.yaml', 'w') as f:
        yaml.dump(demo_data, f, default_flow_style=False, sort_keys=False)
    
    print("Created demo.yaml")

def show_demo():
    """Show the demo"""
    print("YAML FUSE Demo")
    print("===============")
    print()
    
    # Create demo YAML
    create_demo_yaml()
    
    # Show the YAML content
    print("Original YAML file:")
    print("-" * 40)
    with open('demo.yaml', 'r') as f:
        print(f.read())
    print()
    
    # Create mount point
    mount_point = '/tmp/yaml_demo'
    if not os.path.exists(mount_point):
        os.makedirs(mount_point)
    
    print(f"Mounting demo.yaml at {mount_point}")
    print("Press Ctrl+C to stop the demo")
    print()
    
    # Start FUSE
    process = subprocess.Popen([
        sys.executable, 'yaml-fuse.py', 'demo.yaml', mount_point
    ])
    
    try:
        time.sleep(2)  # Wait for mount
        
        print("Filesystem structure:")
        print("-" * 40)
        subprocess.run(['tree', mount_point], capture_output=True, text=True)
        print()
        
        print("Available operations:")
        print("1. Read values: cat /tmp/yaml_demo/app/name")
        print("2. List directories: ls /tmp/yaml_demo/")
        print("3. Read as YAML: cat /tmp/yaml_demo/database.yaml")
        print("4. Read as JSON: cat /tmp/yaml_demo/database.json")
        print("5. Write values: echo 'new_value' > /tmp/yaml_demo/app/new_field")
        print("6. Create directories: mkdir /tmp/yaml_demo/new_section")
        print()
        
        print("Try these commands in another terminal:")
        print(f"  ls -la {mount_point}")
        print(f"  cat {mount_point}/app/name")
        print(f"  cat {mount_point}/database.yaml")
        print(f"  cat {mount_point}/applies_to.yaml")
        print(f"  cat {mount_point}/allowed_ips.yaml")
        print(f"  cat {mount_point}/features.yaml")
        print(f"  cat {mount_point}/dependencies.yaml")
        print(f"  echo 'test' > {mount_point}/app/test_field")
        print(f"  cat {mount_point}/app/test_field")
        print()
        
        print("The YAML file will be updated automatically when you modify files.")
        print("Press Ctrl+C to stop...")
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping demo...")
    finally:
        # Cleanup
        try:
            subprocess.run(['umount', mount_point])
        except:
            pass
        process.terminate()
        process.wait()
        
        # Show final YAML
        print("\nFinal YAML file:")
        print("-" * 40)
        try:
            with open('demo.yaml', 'r') as f:
                print(f.read())
        except FileNotFoundError:
            print("File not found (may have been deleted)")
        
        # Cleanup
        if os.path.exists('demo.yaml'):
            os.remove('demo.yaml')

if __name__ == '__main__':
    show_demo() 