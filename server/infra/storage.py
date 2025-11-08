"""File storage utilities."""
import os
import hashlib
import aiofiles
from pathlib import Path
from typing import Optional
from infra.config import settings


class Storage:
    """Handles file storage and checksum calculation."""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_file(self, file_content: bytes, filename: str) -> tuple[str, str]:
        """
        Save file and return (file_path, checksum).
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Tuple of (relative_path, sha256_checksum)
        """
        # Calculate checksum
        checksum = hashlib.sha256(file_content).hexdigest()
        
        # Create filename with checksum prefix to avoid collisions
        file_ext = Path(filename).suffix
        safe_filename = f"{checksum[:16]}_{Path(filename).stem}{file_ext}"
        file_path = self.base_dir / safe_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        return str(file_path.resolve().relative_to(Path.cwd())), checksum
    
    def calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file."""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def get_file_path(self, filename: str) -> Path:
        """Get full path for a filename."""
        return self.base_dir / filename
    
    def file_exists(self, checksum: str) -> Optional[str]:
        """Check if a file with given checksum exists, return path if found."""
        for file_path in self.base_dir.glob(f"{checksum[:16]}*"):
            return str(file_path)
        return None

