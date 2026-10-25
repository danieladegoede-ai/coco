# Native P2 build and release workflow

The `P2 native build, full tests and release candidate` workflow runs on main,
release branches, pull requests and manual dispatch. The source job uses the cross-platform Python 3.11.9 distribution and calls the
retained full baseline plus four disjoint edge shards on Linux/Windows. Native
builds happen on Windows 2022 x64, Ubuntu 22.04 x64 and macOS 14 arm64, using
Python 3.13.7 and pinned `packaging/requirements-build.txt` dependencies.
PyInstaller is not a cross-compiler: each platform builds its own executable.

```sh
python3 -m pip install -r packaging/requirements-build.txt
python3 tools/build_native.py --output dist/native
python3 ci/test_packaged_p2.py --executable dist/native/group-2 --report build/native-acceptance.json
python3 tools/run_edge_5000.py --executable dist/native/group-2 --workers 4
# Windows uses dist/native/group-2.exe.
```

`build_native.py` requires a clean committed checkout. Development-only
`--allow-dirty` output is marked dirty and cannot enter the release assembler.
The manifest records source commit/tree, versions, native format/CPU, build
argv, size and SHA-256. The launcher standardizes diagnostics to UTF-8.
The compiler has no external Python/pip runtime dependency; generated C++
execution still requires a C++ toolchain as the manual explains.

Native artifacts are uploaded only after clean-directory launch, the semantic
manifest, target compile/run manifest and black-box tests pass. Four downstream
shards per OS run the exact same 5,000 unittest methods against the downloaded
final binary, comparing emitted XML/C++ with the source APIs too. Reports record
the binary hash before/after. A separate Ubuntu 24 job checks all hand-authored
target cases using `g++-13` and `gcc-13 -x c++ ... -lstdc++`, implementing A34.

## LaTeX manual

```sh
# Install texlive-latex-extra, texlive-fonts-recommended and poppler-utils.
python3 tools/build_manual.py --output output/pdf
# Or pass --engine /path/to/tectonic.
```

The source is `release/group-2.tex`. The builder inserts the current source
commit, compiles LaTeX, rejects overfull boxes, checks required text and five
pages, and creates `manual-manifest.json`. Render the final PDF with pdftoppm
and visually inspect every page. Eight personal signature lines remain blank.
No software-generated tick or typed owner name is represented as a signature.
The manual manifest binds those checks to the PDF's exact SHA-256 and size;
assembly rejects a missing or replaced PDF rather than trusting its page-count
record alone.

## Assembly and delivery

After all source/native/package/GNU/manual gates pass, assembly verifies the
same source commit and all binary hashes, accepts exactly 5,000 distinct passed
case IDs per platform without skips, then creates `group-2-candidate.zip` and an
external checksum receipt. It includes only the documented executables, manual,
examples and manifest. Fresh jobs on all three operating systems extract this
ZIP outside the checkout, verify payload hashes, follow the manual, run the
example C++ and check the semantic-invalid example. Only then is a **draft GitHub
release** created, explicitly labelled as requiring personal signatures.
Assembly also rechecks native file formats/CPUs, filenames/sizes, the black-box
gate and that both GNU compatibility reports name the unchanged Linux binary
being shipped. Reports from another binary cannot certify the candidate.

Download the `group-2-release-candidate` workflow artifact or the draft release.
Each member signs both declarations personally. Preserve a signed manual,
reassemble the final `group-2.zip` with matching updated hashes, review the exact
archive and upload only in the First Class ClickUp slot. Retain the receipt and
verify the downloaded copy. The portal closing hour was not provided; no time,
signature, member consent or upload is invented by this workflow.
