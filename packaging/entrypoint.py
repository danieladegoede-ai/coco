"""Native console entry point; diagnostics use UTF-8 on every platform."""
import sys
from spl_frontend.cli import main

if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
