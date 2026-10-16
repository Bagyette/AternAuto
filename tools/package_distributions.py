"""Compatibility entry point for the shared v2 packager."""
import sys
from distributions_v2 import main

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "package"]
    main()
