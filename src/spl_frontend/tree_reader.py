"""Read the existing flat P1 XML schema, retaining IDs and ordered links."""

from __future__ import annotations

from pathlib import Path
import re
from xml.etree import ElementTree as ET

from spl_frontend.semantic_model import FoundationError
from spl_frontend.tree import NodeKind, SyntaxTree, TreeNode


class _SchemaBuilder(ET.TreeBuilder):
    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise ValueError("The syntax_tree schema does not contain a document type.")


def _container(element: ET.Element) -> None:
    if element.attrib or (element.text or "").strip():
        raise ValueError(f"Unexpected attributes/text in <{element.tag}>.")
    if any((child.tail or "").strip() for child in element):
        raise ValueError(f"Unexpected mixed text in <{element.tag}>.")


def _scalar(element: ET.Element) -> str:
    if element.attrib or len(element):
        raise ValueError(f"<{element.tag}> must contain text only.")
    return element.text or ""


def _id(element: ET.Element) -> int:
    value = _scalar(element).strip()
    if not re.fullmatch(r"[1-9][0-9]*", value):
        raise ValueError(f"<{element.tag}> needs a positive decimal integer, got {value!r}.")
    return int(value)


def parse_tree_xml(data: str | bytes, path: Path = Path("tree.xml")) -> SyntaxTree:
    """Parse a complete XML document or raise a structured FoundationError.

    The schema/graph is validated, not the full SPL grammar. Root-only P1
    structural fixtures are supported. List/function walkers check the local
    grammar shapes they consume. XML record order is immaterial; children
    order and every original contents string remain significant.
    """
    try:
        document = ET.fromstring(data, parser=ET.XMLParser(target=_SchemaBuilder()))
    except (ET.ParseError, ValueError) as exc:
        raise FoundationError("XML-PARSE", str(exc), path=path) from exc
    try:
        if document.tag != "syntax_tree":
            raise ValueError("Expected <syntax_tree> document root.")
        _container(document)
        records = []
        for entry in document:
            try:
                kind = NodeKind(entry.tag)
            except ValueError as exc:
                raise ValueError(f"Unknown node record <{entry.tag}>.") from exc
            _container(entry)
            fields = {child.tag: child for child in entry}
            expected = {"id", "contents"}
            if kind is not NodeKind.ROOT:
                expected.add("parent")
            if kind is not NodeKind.LEAF:
                expected.add("children")
            if len(fields) != len(entry) or set(fields) != expected:
                raise ValueError(f"<{entry.tag}> has missing, duplicate or unexpected fields.")
            child_ids = []
            if "children" in fields:
                children = fields["children"]
                _container(children)
                for child in children:
                    if child.tag != "child":
                        raise ValueError("<children> may contain only <child> IDs.")
                    child_ids.append(_id(child))
            records.append(TreeNode(
                _id(fields["id"]), kind, _scalar(fields["contents"]),
                _id(fields["parent"]) if "parent" in fields else None,
                child_ids,
            ))
        return SyntaxTree.from_nodes(records)
    except (ValueError, TypeError) as exc:
        raise FoundationError("XML-TREE", str(exc), path=path) from exc


def read_tree(path: str | Path) -> SyntaxTree:
    source = Path(path)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise FoundationError("XML-READ", f"Cannot read syntax tree: {exc}", path=source) from exc
    return parse_tree_xml(data, source)
