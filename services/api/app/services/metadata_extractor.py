"""
Comprehensive audio metadata extraction service using mutagen.
Extracts full metadata from audio files including ID3 tags, duration, bitrate, etc.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog
from mutagen import File as MutagenFile
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis

logger = structlog.get_logger()


class MetadataExtractor:
    """Extracts comprehensive metadata from audio files"""
    
    SUPPORTED_FORMATS = {'.mp3', '.flac', '.m4a', '.mp4', '.ogg', '.wav', '.aac'}
    
    @classmethod
    async def extract_file_metadata(cls, file_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from a single audio file
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing extracted metadata
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                logger.warning("Audio file not found", path=file_path)
                return cls._empty_metadata(file_path)
            
            if path.suffix.lower() not in cls.SUPPORTED_FORMATS:
                logger.info("Unsupported audio format", path=file_path, suffix=path.suffix)
                return cls._empty_metadata(file_path)
            
            # Load audio file with mutagen
            audio_file = MutagenFile(file_path)
            if audio_file is None:
                logger.warning("Could not load audio file", path=file_path)
                return cls._empty_metadata(file_path)
            
            # Extract basic file information
            file_stats = path.stat()
            metadata = {
                'file_path': file_path,
                'filename': path.name,
                'file_size_bytes': file_stats.st_size,
                'file_modified_at': file_stats.st_mtime,
                'format': path.suffix.lower().lstrip('.'),
                'codec': cls._get_codec_info(audio_file),
            }
            
            # Extract audio properties
            if hasattr(audio_file, 'info') and audio_file.info:
                info = audio_file.info
                metadata.update({
                    'duration_sec': getattr(info, 'length', None),
                    'bitrate': getattr(info, 'bitrate', None),
                    'sample_rate': getattr(info, 'sample_rate', None),
                    'channels': getattr(info, 'channels', None),
                    'bits_per_sample': getattr(info, 'bits_per_sample', None),
                })
            
            # Extract tags
            if audio_file.tags:
                metadata.update(cls._extract_tags(audio_file.tags, path.suffix.lower()))
            
            # Clean and normalize metadata
            metadata = cls._normalize_metadata(metadata)
            
            logger.debug("Extracted metadata", file_path=file_path, 
                        title=metadata.get('title'), artist=metadata.get('artist'))
            
            return metadata
            
        except Exception as e:
            logger.error("Failed to extract metadata", file_path=file_path, error=str(e))
            return cls._empty_metadata(file_path, error=str(e))
    
    @classmethod
    async def scan_directory(cls, directory_path: str, recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Scan a directory for audio files and extract metadata from all
        
        Args:
            directory_path: Path to directory to scan
            recursive: Whether to scan subdirectories recursively
            
        Returns:
            List of metadata dictionaries
        """
        results = []
        path = Path(directory_path)
        
        if not path.exists() or not path.is_dir():
            logger.warning("Directory not found or not a directory", path=directory_path)
            return results
        
        try:
            # Get all audio files
            pattern = "**/*" if recursive else "*"
            audio_files = []
            
            for file_path in path.glob(pattern):
                if file_path.is_file() and file_path.suffix.lower() in cls.SUPPORTED_FORMATS:
                    audio_files.append(str(file_path))
            
            logger.info("Found audio files for scanning", count=len(audio_files), directory=directory_path)
            
            # Extract metadata from each file
            for file_path in audio_files:
                metadata = await cls.extract_file_metadata(file_path)
                if metadata:
                    results.append(metadata)
            
            return results
            
        except Exception as e:
            logger.error("Failed to scan directory", directory=directory_path, error=str(e))
            return results
    
    @classmethod
    def _extract_tags(cls, tags, file_format: str) -> Dict[str, Any]:
        """Extract tags based on file format"""
        metadata = {}
        
        if file_format == '.mp3':
            metadata.update(cls._extract_id3_tags(tags))
        elif file_format == '.flac':
            metadata.update(cls._extract_vorbis_tags(tags))
        elif file_format in ['.m4a', '.mp4']:
            metadata.update(cls._extract_mp4_tags(tags))
        elif file_format == '.ogg':
            metadata.update(cls._extract_vorbis_tags(tags))
        else:
            # Generic tag extraction
            metadata.update(cls._extract_generic_tags(tags))
        
        return metadata
    
    @classmethod
    def _extract_id3_tags(cls, tags) -> Dict[str, Any]:
        """Extract ID3 tags from MP3 files"""
        metadata = {}
        
        # Standard ID3 tags
        tag_mapping = {
            'TIT2': 'title',           # Title
            'TPE1': 'artist',          # Artist
            'TALB': 'album',           # Album
            'TDRC': 'year',            # Year
            'TCON': 'genre',           # Genre
            'TRCK': 'track_number',    # Track number
            'TPE2': 'album_artist',    # Album artist
            'TPOS': 'disc_number',     # Disc number
            'TLEN': 'duration_ms',     # Length in milliseconds
            'TBPM': 'bpm',             # BPM
            'TKEY': 'key',             # Musical key
            'TPE3': 'conductor',       # Conductor
            'TCOM': 'composer',        # Composer
            'TPUB': 'publisher',       # Publisher
            'TCOP': 'copyright',       # Copyright
            'COMM::eng': 'comment',    # Comment
        }
        
        for id3_key, meta_key in tag_mapping.items():
            if id3_key in tags:
                value = str(tags[id3_key][0]) if hasattr(tags[id3_key], '__getitem__') else str(tags[id3_key])
                if value.strip():
                    metadata[meta_key] = value.strip()
        
        # Extract album art
        if 'APIC:' in tags:
            metadata['has_artwork'] = True
        
        return metadata
    
    @classmethod
    def _extract_vorbis_tags(cls, tags) -> Dict[str, Any]:
        """Extract Vorbis comments (FLAC, OGG)"""
        metadata = {}
        
        tag_mapping = {
            'TITLE': 'title',
            'ARTIST': 'artist',
            'ALBUM': 'album',
            'DATE': 'year',
            'GENRE': 'genre',
            'TRACKNUMBER': 'track_number',
            'ALBUMARTIST': 'album_artist',
            'DISCNUMBER': 'disc_number',
            'BPM': 'bpm',
            'COMPOSER': 'composer',
            'COMMENT': 'comment',
        }
        
        for vorbis_key, meta_key in tag_mapping.items():
            if vorbis_key in tags:
                value = tags[vorbis_key][0] if isinstance(tags[vorbis_key], list) else str(tags[vorbis_key])
                if value.strip():
                    metadata[meta_key] = value.strip()
        
        return metadata
    
    @classmethod
    def _extract_mp4_tags(cls, tags) -> Dict[str, Any]:
        """Extract MP4/M4A tags"""
        metadata = {}
        
        tag_mapping = {
            '\xa9nam': 'title',
            '\xa9ART': 'artist',
            '\xa9alb': 'album',
            '\xa9day': 'year',
            '\xa9gen': 'genre',
            'trkn': 'track_number',
            'aART': 'album_artist',
            'disk': 'disc_number',
            'tmpo': 'bpm',
            '\xa9wrt': 'composer',
            '\xa9cmt': 'comment',
        }
        
        for mp4_key, meta_key in tag_mapping.items():
            if mp4_key in tags:
                value = tags[mp4_key]
                if isinstance(value, list) and value:
                    value = value[0]
                if isinstance(value, tuple):
                    value = value[0]  # For track/disc numbers
                metadata[meta_key] = str(value).strip()
        
        # Check for cover art
        if 'covr' in tags:
            metadata['has_artwork'] = True
        
        return metadata
    
    @classmethod
    def _extract_generic_tags(cls, tags) -> Dict[str, Any]:
        """Generic tag extraction for unknown formats"""
        metadata = {}
        
        # Try common tag names
        common_tags = ['title', 'artist', 'album', 'date', 'genre', 'tracknumber']
        for tag in common_tags:
            if tag in tags:
                value = tags[tag][0] if isinstance(tags[tag], list) else str(tags[tag])
                if value.strip():
                    if tag == 'date':
                        metadata['year'] = value.strip()
                    elif tag == 'tracknumber':
                        metadata['track_number'] = value.strip()
                    else:
                        metadata[tag] = value.strip()
        
        return metadata
    
    @classmethod
    def _get_codec_info(cls, audio_file) -> Optional[str]:
        """Get codec information from audio file"""
        if hasattr(audio_file, 'info') and audio_file.info:
            return getattr(audio_file.info, 'codec', None)
        return None
    
    @classmethod
    def _normalize_metadata(cls, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize extracted metadata"""
        # Parse year from various formats
        if 'year' in metadata:
            year_str = str(metadata['year']).strip()
            # Extract 4-digit year from strings like "2023-01-01" or "2023"
            import re
            year_match = re.search(r'\b(19|20)\d{2}\b', year_str)
            if year_match:
                try:
                    metadata['year'] = int(year_match.group())
                except ValueError:
                    del metadata['year']
            else:
                del metadata['year']
        
        # Parse track numbers from "1/12" format
        if 'track_number' in metadata:
            track_str = str(metadata['track_number']).strip()
            if '/' in track_str:
                track_str = track_str.split('/')[0]
            try:
                metadata['track_number'] = int(track_str)
            except ValueError:
                del metadata['track_number']
        
        # Parse disc numbers
        if 'disc_number' in metadata:
            disc_str = str(metadata['disc_number']).strip()
            if '/' in disc_str:
                disc_str = disc_str.split('/')[0]
            try:
                metadata['disc_number'] = int(disc_str)
            except ValueError:
                del metadata['disc_number']
        
        # Parse BPM
        if 'bpm' in metadata:
            try:
                metadata['bpm'] = int(float(metadata['bpm']))
            except ValueError:
                del metadata['bpm']
        
        # Clean string fields
        string_fields = ['title', 'artist', 'album', 'genre', 'album_artist', 'composer', 'comment']
        for field in string_fields:
            if field in metadata and metadata[field]:
                # Remove null bytes and extra whitespace
                metadata[field] = str(metadata[field]).replace('\x00', '').strip()
                if not metadata[field]:  # Remove if empty after cleaning
                    del metadata[field]
        
        return metadata
    
    @classmethod
    def _empty_metadata(cls, file_path: str, error: Optional[str] = None) -> Dict[str, Any]:
        """Return empty metadata structure for failed extractions"""
        path = Path(file_path)
        metadata = {
            'file_path': file_path,
            'filename': path.name,
            'format': path.suffix.lower().lstrip('.') if path.suffix else None,
            'extraction_error': error
        }
        
        # Try to get basic file stats even if audio parsing failed
        try:
            if path.exists():
                file_stats = path.stat()
                metadata.update({
                    'file_size_bytes': file_stats.st_size,
                    'file_modified_at': file_stats.st_mtime,
                })
        except Exception:
            pass
        
        return metadata