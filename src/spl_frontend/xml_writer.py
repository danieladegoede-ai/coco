"""Write a validated syntax tree using a provisional, isolated XML schema.

The unconfirmed schema is ``<syntax_tree>`` with one ``<root>``, ``<inner>``
or ``<leaf>`` entry per node. Entries appear in ascending node-ID order.
Each entry has ``<id>`` and ``<contents>``; non-roots also have ``<parent>``.
Root and inner entries always have ``<children>``, containing ordered
``<child>`` IDs or an empty ``<children />`` element. Output uses UTF-8,
two-space indentation, LF newlines and a final LF. The exact tag schema and
nullable-production appearance still require tutor confirmation.

The writer validates before publication, writes, flushes and syncs a unique
temporary sibling, checks that temporary XML and its decoded contents, then
atomically replaces the destination. XML normalization that would change
contents is rejected.
It keeps any previous output if it cannot produce a replacement. The compiler
driver owns removal or invalidation of stale output at the start of a new
compilation. The parser never needs XML tags or element-building helpers.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

from spl_frontend.tree import NodeKind, SyntaxTree, TreeNode


def _text_element(parent: ET.Element, tag: str, value: str | int) -> None:
    ET.SubElement(parent, tag).text = str(value)


def _node_element(node: TreeNode) -> ET.Element:
    """Convert one validated node without changing the managed tree node."""
    element = ET.Element(node.kind.value)
    _text_element(element, "id", node.node_id)
    _text_element(element, "contents", node.contents)
    if node.kind is not NodeKind.ROOT:
        assert node.parent_id is not None  # Established by tree.validate().
        _text_element(element, "parent", node.parent_id)
    if node.kind is not NodeKind.LEAF:
        children = ET.SubElement(element, "children")
        for child_id in node.child_ids:
            _text_element(children, "child", child_id)
    return element


def _document(tree: SyntaxTree) -> ET.ElementTree:
    root = ET.Element("syntax_tree")
    for node in tree.iter_nodes():
        root.append(_node_element(node))
    ET.indent(root, space="  ")
    return ET.ElementTree(root)


def _output_path(output_path: str | Path) -> Path:
    destination = Path(output_path)
    parent = destination.parent
    if not parent.exists():
        raise FileNotFoundError(f"Output parent directory does not exist: {parent}")
    if not parent.is_dir():
        raise NotADirectoryError(f"Output parent is not a directory: {parent}")
    if destination.is_dir():
        raise IsADirectoryError(f"XML destination is a directory: {destination}")
    if destination.is_symlink() or (
        destination.exists() and not destination.is_file()
    ):
        raise ValueError(f"XML destination is not a regular file: {destination}")
    return destination


def _verify_contents(tree: SyntaxTree, temporary_path: Path) -> None:
    """Reject XML text normalization that would change a node's contents."""
    entries = list(ET.parse(temporary_path).getroot())
    nodes = list(tree.iter_nodes())
    if len(entries) != len(nodes):
        raise ValueError("Serialized XML does not contain every tree node.")
    for entry, node in zip(entries, nodes):
        if entry.findtext("contents") != node.contents:
            raise ValueError(
                f"Node {node.node_id} contents cannot be preserved exactly in XML."
            )


def write_tree(tree: SyntaxTree, output_path: str | Path) -> None:
    """Validate and atomically publish UTF-8 XML to an existing directory.

    ``output_path`` may be a string or Path. Its parent must already exist;
    an existing regular file may be replaced, while a directory, symlink or
    other special destination is rejected. Existing output stays untouched on
    validation, serialization, verification or replacement failure. The
    compiler driver decides whether old output is stale for a new run.

    Integration owner usage::

        tree.validate()
        write_tree(tree, Path("tree.xml"))
    """
    tree.validate()
    destination = _output_path(output_path)
    document = _document(tree)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            document.write(temporary, encoding="utf-8", xml_declaration=True)
            temporary.write(b"\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        _verify_contents(tree, temporary_path)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
