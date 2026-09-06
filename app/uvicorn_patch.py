#!/usr/bin/env python3
import os
import sys
import re

new_argv = []
skip = False

for i, arg in enumerate(sys.argv):
    if skip:
        skip = False
        continue

    if arg == "--port":
        new_argv.append(arg)
        if i + 1 < len(sys.argv):
            val = sys.argv[i + 1]
            digits = "".join(filter(str.isdigit, str(val)))
            if not digits:
                digits = "".join(filter(str.isdigit, os.environ.get("PORT", ""))) or "8000"
            new_argv.append(digits)
            skip = True
        else:
            new_argv.append("8000")
    elif arg.startswith("--port="):
        val = arg.split("=", 1)[1]
        digits = "".join(filter(str.isdigit, str(val)))
        if not digits:
            digits = "".join(filter(str.isdigit, os.environ.get("PORT", ""))) or "8000"
        new_argv.append(f"--port={digits}")
    else:
        new_argv.append(arg)

sys.argv = new_argv

from uvicorn.main import main

if __name__ == "__main__":
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(main())
