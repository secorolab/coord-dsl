# SPDX-License-Identifier: MPL-2.0
# Author: Minh Nguyen

import shutil
import subprocess
from pathlib import Path


def write_dot(dot_source, output_path, img_format):
    """Write a graphviz graph, rendering it to an image unless the format is `dot`."""
    if img_format == "dot":
        Path(output_path).write_text(dot_source)
        return
    if shutil.which("dot") is None:
        raise ValueError(f"graphviz is needed to write {img_format!r}: no 'dot' on PATH")
    subprocess.run(
        ["dot", f"-T{img_format}", "-o", str(output_path)],
        input=dot_source, text=True, check=True,
    )
