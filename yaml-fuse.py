#!/usr/bin/env python3
"""
YAML FUSE Filesystem

This tool creates a FUSE filesystem that maps YAML structure to a filesystem hierarchy.
Each key in the YAML becomes a file or directory, and nested structures become subdirectories.

Usage:
    python yaml-fuse.py <yaml_file> <mount_point> [--mode yaml|json]

Features:
    - Maps YAML structure to filesystem hierarchy
    - Supports both YAML and JSON output formats
    - Handles nested dictionaries and lists
    - Ephemeral files (starting with .) for temporary data
    - Automatic YAML reloading when source file changes
    - Preserves YAML formatting and structure
"""

import os
import sys
import errno
import yaml
import stat
import time
import json
import argparse
import logging

# Conditional FUSE import for CI environments
try:
    from fuse import FUSE, Operations, LoggingMixIn
    FUSE_AVAILABLE = True
except (ImportError, OSError) as e:
    # FUSE not available (e.g., in CI environment)
    FUSE_AVAILABLE = False
    # Create dummy classes for testing
    class FUSE:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("FUSE not available")
    
    class Operations:
        pass
    
    class LoggingMixIn:
        pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

class YAMLFuse(LoggingMixIn, Operations):
    """
    FUSE filesystem that maps YAML structure to filesystem hierarchy.
    
    Each key in the YAML becomes a file or directory:
    - Dictionaries become directories
    - Lists become directories with numeric keys
    - Strings, numbers, booleans become files
    - Files can be accessed with .yaml or .json suffix for different formats
    """
    
    def __init__(self, yaml_path, default_mode='yaml'):
        self.yaml_path = yaml_path
        self.default_mode = default_mode
        self._load_yaml()
        self.dirty = False
        self.last_mtime = os.path.getmtime(self.yaml_path)
        self.ephemeral_files = {}
        self.file_handles = {}
        self.write_buffers = {}
        self.cache_invalidated = False

    def _load_yaml(self):
        """Load YAML file with error handling"""
        try:
            with open(self.yaml_path, 'r', encoding='utf-8') as f:
                self.data = yaml.load(f, Loader=yaml.Loader) or {}
            
            # Convert quoted strings with \n to actual multiline strings
            self._convert_quoted_strings(self.data)
        except FileNotFoundError:
            logger.warning(f"YAML file {self.yaml_path} not found, starting with empty data")
            self.data = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file: {e}")
            self.data = {}
    
    def _convert_quoted_strings(self, obj):
        """Convert quoted strings with \n to actual multiline strings"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and '\\n' in value:
                    # Convert \n to actual newlines
                    obj[key] = value.replace('\\n', '\n')
                elif isinstance(value, (dict, list)):
                    self._convert_quoted_strings(value)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    self._convert_quoted_strings(item)

    def _save_yaml(self):
        """Save YAML file with error handling"""
        try:
            with open(self.yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.data, f, Dumper=BlockStyleDumper, default_flow_style=False, 
                          sort_keys=False, width=float("inf"), allow_unicode=True, 
                          explicit_end=False, default_style=None)
            self.dirty = False
            self.last_mtime = os.path.getmtime(self.yaml_path)
        except Exception as e:
            logger.error(f"Error saving YAML file: {e}")

    def _reload_if_needed(self):
        """Reload YAML if source file has changed"""
        try:
            mtime = os.path.getmtime(self.yaml_path)
            if mtime > self.last_mtime:
                self._load_yaml()
                self.last_mtime = mtime
        except OSError:
            pass  # File might not exist yet

    def _invalidate_cache(self):
        """Mark cache as invalidated to force refresh"""
        self.cache_invalidated = True

    def _is_ephemeral(self, path):
        """Check if path is an ephemeral file (starts with .)"""
        return os.path.basename(path).startswith('.')

    def _strip_suffix(self, path):
        """Strip file extension and return path and mode"""
        if path.endswith('.json'):
            return path[:-5], 'json'
        elif path.endswith('.yaml') or path.endswith('.yml'):
            return path[:-5] if path.endswith('.yaml') else path[:-4], 'yaml'
        else:
            return path, self.default_mode

    def _resolve_path(self, path, create_missing=False):
        """Resolve filesystem path to YAML structure"""
        self._reload_if_needed()
        
        if path == '/' or path == '':
            return self.data, None
            
        parts = path.strip('/').split('/')
        current = self.data
        
        for part in parts[:-1]:
            if isinstance(current, dict):
                if part not in current:
                    if create_missing:
                        current[part] = {}
                    else:
                        return None, None
                current = current[part]
            elif isinstance(current, list):
                try:
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None, None
                except ValueError:
                    return None, None
            else:
                return None, None
                
        return current, parts[-1]

    def _get_value_content(self, value, mode='yaml'):
        """Get content for a value in specified mode"""
        if isinstance(value, str):
            # For strings, output the content directly
            return value.encode('utf-8')
        elif mode == 'json':
            return json.dumps(value, indent=2, ensure_ascii=False).encode('utf-8')
        else:
            # For YAML mode, use block style to preserve formatting
            return yaml.dump(value, Dumper=BlockStyleDumper, default_flow_style=False, 
                           sort_keys=False, allow_unicode=True, width=float("inf"), 
                           explicit_end=False).encode('utf-8')

    def readdir(self, path, fh):
        """List directory contents"""
        # Force reload if cache was invalidated
        if self.cache_invalidated:
            self._reload_if_needed()
            self.cache_invalidated = False
            
        parent, key = self._resolve_path(path)
        if key is not None:
            if isinstance(parent, dict):
                parent = parent.get(key)
            elif isinstance(parent, list):
                try:
                    index = int(key)
                    if 0 <= index < len(parent):
                        parent = parent[index]
                    else:
                        parent = None
                except ValueError:
                    parent = None
        
        if parent is None:
            return ['.', '..']
            
        keys = []
        if isinstance(parent, dict):
            keys = list(parent.keys())
        # Lists are now treated as files, not directories
            
        # Add ephemeral files
        ephemerals = []
        for p in self.ephemeral_files:
            parts = p.strip('/').split('/')
            if len(parts) == 1 and path == '/':
                ephemerals.append(parts[0])
            elif '/'.join(parts[:-1]) == path.strip('/'):
                ephemerals.append(parts[-1])
                
        return ['.', '..'] + keys + ephemerals

    def getattr(self, path, fh=None):
        """Get file attributes"""
        if self._is_ephemeral(path):
            if path not in self.ephemeral_files:
                raise OSError(errno.ENOENT, '')
            content = self.ephemeral_files.get(path, b'')
            return dict(st_mode=stat.S_IFREG | 0o644, st_nlink=1, st_size=len(content))

        stripped_path, mode = self._strip_suffix(path)

        if stripped_path == '/':
            return dict(st_mode=(stat.S_IFDIR | 0o755), st_nlink=2)

        parent, key = self._resolve_path(stripped_path)
        if parent is None:
            raise OSError(errno.ENOENT, '')

        if key is None:
            return dict(st_mode=(stat.S_IFDIR | 0o755), st_nlink=2)

        target = parent.get(key) if isinstance(parent, dict) else None
        if isinstance(parent, list):
            try:
                index = int(key)
                if 0 <= index < len(parent):
                    target = parent[index]
            except ValueError:
                pass
                
        if target is None:
            raise OSError(errno.ENOENT, '')

        if isinstance(target, dict):
            return dict(st_mode=(stat.S_IFDIR | 0o755), st_nlink=2)
        else:
            content = self._get_value_content(target, mode)
            return dict(st_mode=(stat.S_IFREG | 0o644), st_nlink=1, st_size=len(content))

    def open(self, path, flags):
        """Open a file"""
        fh = len(self.file_handles) + 1
        self.file_handles[fh] = path
        return fh

    def read(self, path, size, offset, fh):
        """Read file content"""
        if self._is_ephemeral(path):
            content = self.ephemeral_files.get(path, b'')
            return content[offset:offset + size]

        stripped_path, mode = self._strip_suffix(path)
        parent, key = self._resolve_path(stripped_path)
        if key is None:
            return b''

        value = None
        if isinstance(parent, dict):
            value = parent.get(key)
        elif isinstance(parent, list):
            try:
                index = int(key)
                if 0 <= index < len(parent):
                    value = parent[index]
            except ValueError:
                pass

        if value is None:
            return b''

        content = self._get_value_content(value, mode)
        return content[offset:offset + size]

    def write(self, path, data, offset, fh):
        """Write to file"""
        if self._is_ephemeral(path):
            current = self.ephemeral_files.get(path, b'')
            if not isinstance(current, bytes):
                current = current.encode('utf-8')
            content = current[:offset] + data
            self.ephemeral_files[path] = content
            return len(data)

        # Accumulate data in write buffer
        if fh not in self.write_buffers:
            self.write_buffers[fh] = b''
        
        # Add new data to buffer
        if offset == 0:
            # Start of write, replace buffer
            self.write_buffers[fh] = data
        else:
            # Append to existing buffer
            self.write_buffers[fh] += data
        
        return len(data)

    def truncate(self, path, length, fh=None):
        """Truncate file"""
        if self._is_ephemeral(path):
            content = self.ephemeral_files.get(path, b'')
            self.ephemeral_files[path] = content[:length]
            return

        stripped_path, _ = self._strip_suffix(path)
        parent, key = self._resolve_path(stripped_path, create_missing=True)
        
        if isinstance(parent, dict):
            parent[key] = ""
        else:
            raise OSError(errno.ENOTDIR, '')
                
        self.dirty = True

    def create(self, path, mode):
        """Create a new file"""
        if self._is_ephemeral(path):
            self.ephemeral_files[path] = b''
            return 42

        stripped_path, _ = self._strip_suffix(path)
        parent, key = self._resolve_path(stripped_path, create_missing=True)
        
        if isinstance(parent, dict):
            parent[key] = ""
        else:
            raise OSError(errno.ENOTDIR, '')
                
        self.dirty = True
        self._invalidate_cache()
        return 42

    def unlink(self, path):
        """Delete a file"""
        if self._is_ephemeral(path):
            self.ephemeral_files.pop(path, None)
            return

        stripped_path, _ = self._strip_suffix(path)
        parent, key = self._resolve_path(stripped_path)
        if parent is None or key is None:
            raise OSError(errno.ENOENT, '')
            
        if isinstance(parent, dict) and key in parent:
            del parent[key]
            self.dirty = True
            # Invalidate cache to force refresh
            self._invalidate_cache()
        else:
            raise OSError(errno.ENOENT, '')

    def rmdir(self, path):
        """Remove directory (same as unlink for this implementation)"""
        self.unlink(path)
        # Cache invalidation is handled in unlink

    def mkdir(self, path, mode):
        """Create directory"""
        stripped_path, _ = self._strip_suffix(path)
        parent, key = self._resolve_path(os.path.dirname(stripped_path), create_missing=True)
        full_path = os.path.basename(stripped_path)
        
        if isinstance(parent, dict):
            parent[full_path] = {}
        else:
            raise OSError(errno.ENOTDIR, '')
            
        self.dirty = True
        self._invalidate_cache()
        return 0

    def flush(self, path, fh):
        """Flush changes to disk"""
        if self.dirty:
            self._save_yaml()

    def release(self, path, fh):
        """Release file handle and save if dirty"""
        # Process accumulated write data
        if fh in self.write_buffers:
            data = self.write_buffers[fh]
            del self.write_buffers[fh]
            
            # Process the complete data
            stripped_path, _ = self._strip_suffix(path)
            parent, key = self._resolve_path(stripped_path, create_missing=True)

            try:
                content = data.decode('utf-8')
                stripped = content.rstrip('\n')
                
                # Always try to parse as YAML first
                try:
                    parsed_yaml = yaml.safe_load(content)
                    logger.debug(f"YAML parsing result for {path}: {parsed_yaml}")
                    # If parsing succeeds and the result is not None, use the parsed value
                    if parsed_yaml is not None:
                        new_value = parsed_yaml
                        logger.debug(f"Using parsed YAML structure for {path}")
                    else:
                        # If YAML parsing returns None, treat as empty string
                        new_value = ""
                        logger.debug(f"YAML parsing returned None, using empty string for {path}")
                except yaml.YAMLError as e:
                    logger.debug(f"YAML parsing failed for {path}: {e}")
                    # If YAML parsing fails, treat as string
                    if '\n' in stripped and len(stripped.split('\n')) > 1:
                        # For actual multiline content, preserve as string
                        new_value = content
                        logger.debug(f"Using multiline string for {path}")
                    else:
                        # For single-line content, treat as string
                        new_value = content.rstrip('\n')
                        logger.debug(f"Using single-line string for {path}")
            except Exception as e:
                new_value = data.decode('utf-8', errors='replace')
                logger.error(f"Error processing content: {e}")

            if isinstance(parent, dict):
                parent[key] = new_value
            elif isinstance(parent, list):
                try:
                    index = int(key)
                    while len(parent) <= index:
                        parent.append(None)
                    parent[index] = new_value
                except ValueError:
                    parent.append(new_value)
                    
            self.dirty = True
            self._invalidate_cache()
        
        if self.dirty:
            self._save_yaml()
        if fh in self.file_handles:
            del self.file_handles[fh]

    def fsync(self, path, datasync, fh):
        """Sync file to disk"""
        if self.dirty:
            self._save_yaml()
        return 0

    def access(self, path, mode):
        """Check file access permissions"""
        try:
            self.getattr(path)
        except OSError:
            raise OSError(errno.ENOENT, '')
        return 0

    def utimens(self, path, times=None):
        """Update file timestamps"""
        return 0

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Mount a YAML file as a filesystem using FUSE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python yaml-fuse.py config.yaml /mnt/config
  python yaml-fuse.py data.yaml /tmp/data --mode json
        """
    )
    parser.add_argument('yaml_path', help='Path to YAML file')
    parser.add_argument('mountpoint', help='Mount point')
    parser.add_argument('--mode', choices=['yaml', 'json'], default='yaml', 
                       help='Default serialization mode (default: yaml)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate inputs
    if not os.path.exists(args.mountpoint):
        try:
            os.makedirs(args.mountpoint)
        except OSError as e:
            logger.error(f"Cannot create mount point {args.mountpoint}: {e}")
            sys.exit(1)
    
    if not os.path.isdir(args.mountpoint):
        logger.error(f"Mount point {args.mountpoint} is not a directory")
        sys.exit(1)
    
    logger.info(f"Mounting {args.yaml_path} at {args.mountpoint} with mode={args.mode}")
    
    if not FUSE_AVAILABLE:
        logger.error("FUSE is not available. Cannot mount filesystem.")
        logger.error("This usually means libfuse is not installed or not accessible.")
        sys.exit(1)
    
    try:
        FUSE(YAMLFuse(args.yaml_path, default_mode=args.mode), 
             args.mountpoint, nothreads=True, foreground=True)
    except KeyboardInterrupt:
        logger.info("Unmounting filesystem...")
    except Exception as e:
        logger.error(f"FUSE error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
