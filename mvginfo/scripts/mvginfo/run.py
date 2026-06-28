# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = [
#   "async-mvg-api>=0.3",
#   "pydantic>=2.7",
#   "typer>=0.12",
# ]
# ///

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mvginfo.cli import main

if __name__ == "__main__":
    main()
