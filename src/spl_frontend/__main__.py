"""Enable `python -m spl_frontend`."""

from __future__ import annotations

import sys

from spl_frontend.cli import main

if __name__ == "__main__":
    sys.exit(main())