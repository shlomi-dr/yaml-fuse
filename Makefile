# YAML FUSE Makefile

.PHONY: install test demo clean help

# Default target
all: help

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip3 install -r requirements.txt
	chmod +x yaml-fuse.py
	@echo "Installation complete!"

# Run tests
test: install
	@echo "Running tests..."
	python3 test_example.py

# Run demo
demo: install
	@echo "Running demo..."
	python3 demo.py

# Clean up temporary files
clean:
	@echo "Cleaning up..."
	rm -f test_config.yaml demo.yaml
	@echo "Cleanup complete!"

# Show help
help:
	@echo "YAML FUSE Makefile"
	@echo "=================="
	@echo ""
	@echo "Available targets:"
	@echo "  install  - Install dependencies"
	@echo "  test     - Run test suite"
	@echo "  demo     - Run interactive demo"
	@echo "  clean    - Clean up temporary files"
	@echo "  help     - Show this help message"
	@echo ""
	@echo "Usage examples:"
	@echo "  make install"
	@echo "  make test"
	@echo "  make demo"
	@echo "  python3 yaml-fuse.py config.yaml /mnt/config" 