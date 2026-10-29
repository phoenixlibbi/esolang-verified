"""The vendored upstream files must stay byte-identical to the pinned commit."""
import hashlib

from esoforge.upstream import UPSTREAM_DIR

PINNED = {
    "befunge98_interpreter.py": "ae51aa4585b2cab95e2c0b83a80a3a5043e4f7a9521c309ac60257c2862956fb",
    "brainfuck_interpreter.py": "2352eadab132eab1c5046caf1ff659c80decc4a53a0f626d70cdd5d7ffdec322",
    "esolang_common.py": "6a798715950a8093c70bf7207ee7fe584ffcddb76f20f7e55e0a323dfa916d7f",
    "official_harness.py": "3f80527e9875aebac0ef057009b71fb432d2a62a432185d99bc31db6563be6fc",
    "whitespace_interpreter.py": "2e7bae8599d526c135e36819742d7ca400ee83aeb344896403b6b42b48abd065",
    "prompts/befunge98.md": "4652b049ed896c623209cd64e9478508e9116924e62d015290c31722922e0f25",
    "prompts/brainfuck.md": "43cde37a82aaa89ebe29cab809d3d26b44a2a0f48175594672f68d8451f0ea10",
    "prompts/whitespace.md": "6117a336587ff05a1700b8c030482ed55c86e4ac13ac531e5967bd8127ada535",
}


def test_upstream_files_unmodified():
    for name, digest in PINNED.items():
        assert hashlib.sha256((UPSTREAM_DIR / name).read_bytes()).hexdigest() == digest, name
