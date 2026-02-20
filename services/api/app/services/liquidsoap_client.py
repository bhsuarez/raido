"""
Liquidsoap telnet client for getting real-time metadata and status
"""

import socket
import structlog
from typing import Dict, Any, Optional, List, Tuple
import re
import time
import threading

logger = structlog.get_logger()


class LiquidsoapClient:
    """Client for interacting with Liquidsoap telnet interface"""
    
    def __init__(self, host: str = "liquidsoap", port: int = 1234, timeout: float = 3.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        
        # Cache and rate limiting
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._last_request_time = 0
        self._min_request_interval = 0.2  # Shorter spacing between telnet calls
        self._cache_duration = 2.0  # Cache responses briefly to smooth bursts
    
    def _send_command(self, command: str, use_cache: bool = True) -> str:
        """Send a command to Liquidsoap with caching and rate limiting"""
        
        # Check cache first
        if use_cache:
            with self._cache_lock:
                cache_key = command
                cached_entry = self._cache.get(cache_key)
                if cached_entry:
                    response, timestamp = cached_entry
                    if time.time() - timestamp < self._cache_duration:
                        logger.debug("Using cached response", command=command)
                        return response
        
        # Rate limiting - ensure minimum interval between requests
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            logger.debug("Rate limiting - sleeping", sleep_time=sleep_time)
            time.sleep(sleep_time)
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            
            # Send command
            sock.send(f"{command}\n".encode())
            
            # Read response (support multi-line outputs like request.metadata ... END)
            chunks: List[bytes] = []
            try:
                while True:
                    part = sock.recv(4096)
                    if not part:
                        break
                    chunks.append(part)
                    # Normalize CRLF and check for END terminator anywhere in the buffer
                    buf = b"".join(chunks)
                    buf_normalized = buf.replace(b"\r", b"")
                    if b"\nEND\n" in buf_normalized or buf_normalized.endswith(b"\nEND\n") or buf_normalized.endswith(b"END\n") or buf_normalized.endswith(b"END"):
                        break
            except Exception:
                # On timeout or other recv errors, return what we have so far
                pass

            response = b"".join(chunks).decode(errors="ignore").strip()
            sock.close()
            
            # Update last request time
            self._last_request_time = time.time()
            
            # Cache the response
            if use_cache:
                with self._cache_lock:
                    self._cache[command] = (response, self._last_request_time)
            
            return response
            
        except Exception as e:
            logger.error("Failed to send Liquidsoap command", command=command, error=str(e))
            return ""
    
    def get_help(self) -> List[str]:
        """Get list of available commands"""
        try:
            response = self._send_command("help")
            if response:
                # Parse help output into command list
                lines = response.split('\n')
                commands = []
                for line in lines:
                    if line.strip() and not line.startswith('Available') and ':' in line:
                        command = line.split(':')[0].strip()
                        if command:
                            commands.append(command)
                return commands
            return []
        except Exception as e:
            logger.error("Failed to get Liquidsoap help", error=str(e))
            return []
    
    def get_current_metadata(self) -> Dict[str, Any]:
        """Get metadata for currently playing track"""
        try:
            metadata = {}
            
            # Get current track metadata using the correct Liquidsoap command
            metadata_cmd = "🏴‍☠️_Raido_-_AI_Pirate_Radio.metadata"
            response = self._send_command(metadata_cmd)
            
            if response and response != "ERROR: unknown command":
                logger.debug("Got metadata response", response=response[:200])
                parsed = self._parse_metadata_response(response)
                metadata.update(parsed)
            
            # Get remaining time
            remaining_cmd = "🏴‍☠️_Raido_-_AI_Pirate_Radio.remaining"  
            response = self._send_command(remaining_cmd)
            
            if response and response.replace('.', '').replace('-', '').isdigit():
                metadata['remaining_seconds'] = float(response)
            
            return metadata
            
        except Exception as e:
            logger.error("Failed to get current metadata", error=str(e))
            return {}
    
    def get_queue_info(self) -> Dict[str, Any]:
        """Get information about the current queue"""
        try:
            rids = self.list_request_ids()
            queue_info: Dict[str, Any] = {
                'queue_length': len(rids),
                'rids': rids,
            }
            current_rid, next_ready_rid = self.get_current_and_next_ready_rid(rids)
            queue_info['current_rid'] = current_rid
            queue_info['next_ready_rid'] = next_ready_rid
            return queue_info
            
        except Exception as e:
            logger.error("Failed to get queue info", error=str(e))
            return {}
    
    def get_tts_queue_length(self) -> int:
        """Return the number of items currently queued in tts_q"""
        try:
            resp = self._send_command("tts.queue", use_cache=False)
            # Response is space-separated RIDs, or empty
            resp = resp.strip()
            if not resp or resp == "":
                return 0
            rids = [r for r in resp.split() if r.isdigit()]
            return len(rids)
        except Exception as e:
            logger.warning("Failed to get tts queue length", error=str(e))
            return 0

    def get_uptime(self) -> Optional[float]:
        """Get Liquidsoap uptime"""
        try:
            response = self._send_command("uptime")
            if response and response.replace('.', '').isdigit():
                return float(response)
            return None
        except Exception as e:
            logger.error("Failed to get uptime", error=str(e))
            return None
    
    def skip_track(self) -> bool:
        """Skip the current track"""
        try:
            # Use the correct skip command
            response = self._send_command("music.skip")
            
            if response and "ERROR" not in response:
                logger.info("Successfully skipped track", response=response)
                return True
            
            logger.warning("Skip command failed", response=response)
            return False
            
        except Exception as e:
            logger.error("Failed to skip track", error=str(e))
            return False
    
    def _parse_metadata_response(self, response: str) -> Dict[str, Any]:
        """Parse a metadata response from Liquidsoap"""
        metadata = {}
        
        # Support comma-separated single-line and multi-line (request.metadata ... END)
        if '\n' not in response and ',' in response:
            parts = self._split_metadata_string(response)
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key:
                        metadata[key] = value
            return metadata

        for line in response.splitlines():
            line = line.strip()
            if not line or line == 'END':
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    metadata[key] = value
        
        return metadata
    
    def _split_metadata_string(self, s: str) -> List[str]:
        """Split metadata string on commas, respecting quoted values"""
        parts = []
        current = ""
        in_quotes = False
        quote_char = None
        
        for char in s:
            if char in ['"', "'"] and not in_quotes:
                in_quotes = True
                quote_char = char
                current += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current += char
            elif char == ',' and not in_quotes:
                if current.strip():
                    parts.append(current.strip())
                current = ""
            else:
                current += char
        
        if current.strip():
            parts.append(current.strip())
        
        return parts
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get comprehensive status information"""
        try:
            status = {
                'metadata': self.get_current_metadata(),
                'queue': self.get_queue_info(),
                'uptime': self.get_uptime(),
                'available_commands': self.get_help()[:10]  # First 10 commands
            }
            
            return status
            
        except Exception as e:
            logger.error("Failed to get all status", error=str(e))
            return {}

    # ---------- Request queue helpers ----------
    def list_request_ids(self) -> List[int]:
        """Return list of request IDs from `request.all`."""
        try:
            resp = self._send_command("request.all")
            ids: List[int] = []
            for token in resp.replace('\n', ' ').split():
                if token.isdigit():
                    ids.append(int(token))
            return ids
        except Exception as e:
            logger.error("Failed to list request ids", error=str(e))
            return []

    def get_request_metadata(self, rid: int) -> Dict[str, Any]:
        """Return metadata dict for a request id via `request.metadata <rid>`.

        Use cached command responses to avoid repeated telnet roundtrips within
        a short time window.
        """
        resp = self._send_command(f"request.metadata {rid}", use_cache=True)
        return self._parse_metadata_response(resp)

    def get_current_and_next_ready_rid(self, rids: Optional[List[int]] = None) -> Tuple[Optional[int], Optional[int]]:
        """Identify current and next RIDs.

        Strategy:
        - Prefer the RID with status "playing" as current.
        - Fallback: if none marked playing, use the lowest RID (matches observed telnet behavior).
        - Next: choose the next higher RID after current (regardless of status),
          while still preferring items marked "ready" when available.
        """
        if rids is None:
            rids = self.list_request_ids()
        if not rids:
            return None, None

        sorted_rids = sorted(rids)

        # First pass: gather statuses
        statuses: dict[int, str] = {}
        for rid in sorted_rids:
            meta = self.get_request_metadata(rid)
            statuses[rid] = (meta.get('status') or '').lower()

        # Determine current
        playing_rids = [rid for rid in sorted_rids if statuses.get(rid) == 'playing']
        current: Optional[int] = playing_rids[0] if playing_rids else sorted_rids[0]

        # Determine next
        higher_rids = [rid for rid in sorted_rids if rid > current]
        if not higher_rids:
            return current, None

        # Prefer the first higher rid with status ready, else just the next sequential rid
        for rid in higher_rids:
            if statuses.get(rid) == 'ready':
                return current, rid
        return current, higher_rids[0]

    def get_next_ready_track_metadata(self) -> Optional[Dict[str, Any]]:
        """Return metadata dict for the next ready request, or None."""
        _, next_rid = self.get_current_and_next_ready_rid()
        if next_rid is None:
            return None
        return self.get_request_metadata(next_rid)
