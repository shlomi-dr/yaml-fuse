#!/bin/bash

# YAML FUSE Installation Script

set -e

echo "YAML FUSE Installation Script"
echo "============================="

# Function to check if macFUSE is available and working
check_macfuse_available() {
    # Check if macFUSE kernel extension is loaded
    if kextstat | grep -q "macfuse"; then
        return 0
    fi
    
    # Check if FUSE mount is available
    if command -v mount_fusefs &> /dev/null; then
        return 0
    fi
    
    return 1
}

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    echo "Please install Python 3 and try again."
    exit 1
fi

echo "  Python 3 found: $(python3 --version)"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is required but not installed."
    echo "Please install pip3 and try again."
    exit 1
fi

echo "  pip3 found: $(pip3 --version)"

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Check for FUSE
echo "Checking for FUSE support..."

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "  Detected macOS"
    echo ""
    
    # Check if macFUSE is available and working
    if check_macfuse_available; then
        echo "  ✓ macFUSE is available and ready to use!"
        echo ""
    else
        echo "  For macOS, macFUSE installation is required."
        echo ""
        echo "  RECOMMENDED: Download from the official website:"
        echo "    https://github.com/macfuse/macfuse/wiki/Getting-Started"
        echo ""
        echo "  Note: The official documentation recommends against using package managers."
        echo "  You will need to enable a kernel extension feature by rebooting your machine (one time)."
        echo ""
        
        # Check if macFUSE is installed but not available (needs reboot)
        if command -v brew &> /dev/null && brew list | grep -q macfuse; then
            echo "  macFUSE is installed via Homebrew but not yet available."
            echo "  You need to reboot your machine to enable the kernel extension."
            echo ""
            echo "  After rebooting, run this installer again to verify macFUSE is working."
            echo ""
            exit 0
        fi
        
        echo "  macFUSE not found. How would you like to install it?"
        echo ""
        echo "  1) Download from official website (RECOMMENDED)"
        echo "  2) Install via Homebrew (may install outdated version)"
        echo "  3) Skip for now (install manually later)"
        echo ""
        read -p "  Enter your choice (1-3): " choice
        
        case $choice in
            1)
                echo ""
                echo "  Please visit: https://github.com/macfuse/macfuse/wiki/Getting-Started"
                echo "  Download and install macFUSE from the official website."
                echo ""
                echo "  After installation, you will need to reboot your machine."
                echo "  After rebooting, run this installer again to verify macFUSE is working."
                echo ""
                ;;
            2)
                echo ""
                echo "  Installing macFUSE via Homebrew..."
                if command -v brew &> /dev/null; then
                    brew install macfuse
                    echo "  ✓ macFUSE installed via Homebrew"
                    echo ""
                    echo "  You will need to reboot your machine to enable the kernel extension."
                    echo "  After rebooting, run this installer again to verify macFUSE is working."
                else
                    echo "  Homebrew not found. Please install Homebrew first:"
                    echo "    /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                    echo "  Then run: brew install macfuse"
                fi
                ;;
            3)
                echo ""
                echo "  Skipping macFUSE installation. You can install it manually later."
                echo "  Remember to reboot your machine after installation."
                ;;
            *)
                echo "  Invalid choice. Skipping macFUSE installation."
                ;;
        esac
    fi
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "  Detected Linux"
    
    # Check if FUSE is available
    if ! command -v fusermount &> /dev/null; then
        echo "  FUSE not found. Installing..."
        
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            echo "    Installing via apt-get..."
            sudo apt-get update
            sudo apt-get install -y fuse
        elif command -v yum &> /dev/null; then
            # CentOS/RHEL
            echo "    Installing via yum..."
            sudo yum install -y fuse
        elif command -v dnf &> /dev/null; then
            # Fedora
            echo "    Installing via dnf..."
            sudo dnf install -y fuse
        else
            echo "  Error: Could not determine package manager."
            echo "  Please install FUSE manually for your distribution."
            exit 1
        fi
    else
        echo "  ✓ FUSE already installed"
    fi
    
    # Add user to fuse group
    if groups $USER | grep -q fuse; then
        echo "  ✓ User already in fuse group"
    else
        echo "  Adding user to fuse group..."
        sudo usermod -a -G fuse $USER
        echo "  Note: You may need to log out and back in for group changes to take effect."
    fi
else
    echo "  Warning: Unsupported OS type: $OSTYPE"
    echo "  FUSE installation may need to be done manually."
fi

# Make the script executable
chmod +x yaml-fuse.py

echo ""
echo "Installation completed successfully!"
echo ""
echo "Usage examples:"
echo "  python3 yaml-fuse.py config.yaml /mnt/config"
echo "  python3 yaml-fuse.py data.yaml /tmp/data --mode json"
echo ""
echo "To test the installation, run:"
echo "  python3 test.py"
echo ""
echo "For more information, see README.md" 