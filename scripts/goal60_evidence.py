"""Canonicalize fingerprint paths without relaxing content-hash equality."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def canonical_fingerprint(fingerprint):
    result = {}
    for path, digest in fingerprint.items():
        identity = str((REPO / Path(path)).resolve())
        if identity in result and result[identity] != digest:
            raise ValueError('Conflicting hashes for the same evidence file')
        result[identity] = digest
    return result


def same_fingerprint(left, right):
    return canonical_fingerprint(left) == canonical_fingerprint(right)
