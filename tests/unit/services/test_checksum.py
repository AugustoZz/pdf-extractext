import pytest

from app.services.checksum import calculate_checksum


@pytest.mark.parametrize(
    ("file_bytes", "expected"),
    [
        (
            b"",
            "e3b0c44298fc1c149afbf4c8996fb924"
            "27ae41e4649b934ca495991b7852b855",
        ),
        (
            b"hello",
            "2cf24dba5fb0a30e26e83b2ac5b9e29e"
            "1b161e5c1fa7425e73043362938b9824",
        ),
    ],
)
def test_calculate_checksum_returns_sha256_hex(file_bytes: bytes, expected: str) -> None:
    assert calculate_checksum(file_bytes) == expected