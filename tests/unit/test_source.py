"""Tests for source file loading."""

import tempfile
import unittest
from pathlib import Path

from spl_frontend.source import load_source, SourceFile
from spl_frontend.diagnostics import FrontendError


class TestLoadSource(unittest.TestCase):
    """Tests for the load_source function."""

    def _write_temp(self, content: bytes) -> Path:
        """Write bytes to a temporary file and return its path."""
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        f.write(content)
        f.close()
        path = Path(f.name)
        self.addCleanup(lambda p=path: p.unlink(missing_ok=True))
        return path

    def test_empty_file(self):
        path = self._write_temp(b"")
        src = load_source(path)
        self.assertEqual(src.text, "")
        self.assertEqual(len(src), 0)

    def test_simple_ascii(self):
        path = self._write_temp(b"print nop")
        src = load_source(path)
        self.assertEqual(src.text, "print nop")

    def test_ascii_with_newlines(self):
        path = self._write_temp(b"line1\nline2\r\nline3")
        src = load_source(path)
        self.assertIn("line1", src.text)
        self.assertIn("line2", src.text)
        self.assertIn("line3", src.text)

    def test_non_ascii_rejected(self):
        path = self._write_temp(b"print \xe9")
        with self.assertRaises(FrontendError) as ctx:
            load_source(path)
        self.assertIn("non-ASCII", ctx.exception.diagnostic.message)
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-NON-ASCII")

    def test_non_ascii_position(self):
        path = self._write_temp(b"abc\ndef\xff")
        with self.assertRaises(FrontendError) as ctx:
            load_source(path)
        diag = ctx.exception.diagnostic
        self.assertEqual(diag.line, 2)
        self.assertEqual(diag.column, 4)


class TestSourceFile(unittest.TestCase):
    """Tests for the SourceFile dataclass."""

    def test_immutable(self):
        sf = SourceFile(path=Path("test.txt"), text="hello")
        with self.assertRaises(AttributeError):
            sf.text = "world"

    def test_len(self):
        sf = SourceFile(path=Path("test.txt"), text="hello")
        self.assertEqual(len(sf), 5)


if __name__ == "__main__":
    unittest.main()
