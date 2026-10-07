
import hashlib

def calculate_checksum(file_bytes: bytes) -> str:
    """
        Calcula el checksum SHA-256 del archivo.

        Args:
            file_bytes: Contenido del archivo.

        Returns:
            Hash SHA-256 en formato hexadecimal (64 caracteres).
    """
    return hashlib.sha256(file_bytes).hexdigest()