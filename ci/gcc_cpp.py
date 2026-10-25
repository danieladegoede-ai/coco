#!/usr/bin/env python3
"""GCC driver variant of the manual's C++ command, with explicit libstdc++."""
import os
import shutil
import sys
compiler=shutil.which('gcc-13')
if compiler is None:raise SystemExit('gcc-13 is required for the A34 compatibility gate')
os.execv(compiler,[compiler,'-x','c++',*sys.argv[1:],'-lstdc++'])
