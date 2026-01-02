"""
Request-Response Correlation Tracker v2 with SeqID Support

Provides reliable request-response matching for device communication:
- Tracks pending requests by SeqID (primary) or response type (fallback)
- Timeout handling per request
- Callbacks for response handling
- Thread-safe operation

Protocol v2 uses SeqID for correlation:
- Each request gets a unique SeqID (1-0xFFFE)
- Responses echo the same SeqID
- SeqID=0 is broadcast (no response expected)
- SeqID=0xFFFF is reserved

Usage:
    tracker = RequestTracker()

    # Create request with SeqID from frame
    frame = FrameBuilder.ping()  # Auto-assigns SeqID
    tracker.create_request(
        seq_id=frame.seq_id,
        request_type=MessageType.PING,
        response_type=MessageType.PONG,
        timeout=5.0
    )
    send_frame(encode_frame(frame))

    # Wait for response by SeqID
    response = tracker.wait_for_response_by_seq_id(frame.seq_id, timeout=5.0)

    # In message handler - complete by SeqID from response:
    def on_message(frame):
        tracker.complete_by_seq_id(frame.seq_id, frame.payload)
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class RequestState(Enum):
    """State of a tracked request."""
    PENDING = "pending"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class TrackedRequest:
    """Represents a request being tracked for response."""
    seq_id: int                 # Sequence ID for correlation (primary key)
    request_type: int           # Message type sent
    response_type: int          # Expected response message type
    created_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: float = 5.0
    state: RequestState = RequestState.PENDING
    response_data: Optional[bytes] = None
    error_message: Optional[str] = None
    event: threading.Event = field(default_factory=threading.Event)
    callback: Optional[Callable[[Optional[bytes], Optional[str]], None]] = None
    description: str = ""       # Human-readable description for logging

    @property
    def is_pending(self) -> bool:
        return self.state == RequestState.PENDING

    @property
    def is_expired(self) -> bool:
        if self.state != RequestState.PENDING:
            return False
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.timeout_seconds

    @property
    def elapsed_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()


# Command -> Expected Response mapping
RESPONSE_TYPE_MAP = {
    0x01: 0x02,  # PING -> PONG
    0x10: 0x11,  # GET_INFO -> INFO_RESP
    0x20: 0x21,  # GET_CONFIG -> CONFIG_DATA
    0x22: 0x23,  # SET_CONFIG -> CONFIG_ACK
    0x24: 0x25,  # SAVE_TO_FLASH -> FLASH_ACK
    0x26: 0x27,  # CLEAR_CONFIG -> CLEAR_CONFIG_ACK
    0x40: 0x41,  # SET_CHANNEL -> CHANNEL_ACK
    0x43: 0x44,  # GET_CHANNEL -> CHANNEL_DATA
    0x66: 0x67,  # SET_CHANNEL_CONFIG -> CHANNEL_CONFIG_ACK
    0x68: 0x69,  # LOAD_BINARY_CONFIG -> BINARY_CONFIG_ACK
    0x70: 0x71,  # RESTART_DEVICE -> RESTART_ACK
}


class RequestTracker:
    """Thread-safe request-response correlation tracker with SeqID support.

    Tracks pending requests primarily by SeqID (protocol v2). Each request
    gets a unique SeqID, and responses echo the same SeqID for correlation.

    Features:
    - SeqID-based request-response correlation (primary)
    - Per-request timeouts
    - Synchronous wait_for_response() method
    - Callback support
    - Automatic cleanup of expired requests
    - Statistics tracking
    """

    def __init__(self, cleanup_interval: float = 10.0):
        """Initialize RequestTracker.

        Args:
            cleanup_interval: Seconds between automatic cleanup
        """
        self._lock = threading.RLock()
        # Map: seq_id -> TrackedRequest (primary tracking)
        self._pending_by_seq_id: Dict[int, TrackedRequest] = {}
        # Map: response_type -> TrackedRequest (fallback for legacy)
        self._pending_by_response: Dict[int, TrackedRequest] = {}
        # History of completed requests (for debugging)
        self._completed: List[TrackedRequest] = []
        self._max_history = 50
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

        # Statistics
        self._stats = {
            'requests_created': 0,
            'requests_completed': 0,
            'requests_timeout': 0,
            'requests_error': 0,
            'requests_cancelled': 0,
        }

    def create_request(self, seq_id: int, request_type: int, response_type: int = None,
                       timeout: float = 5.0, callback: Optional[Callable] = None,
                       description: str = "") -> bool:
        """Create a tracked request with SeqID.

        Args:
            seq_id: Sequence ID from the request frame (used for correlation)
            request_type: Message type being sent (e.g., GET_CONFIG=0x20)
            response_type: Expected response type (auto-determined if None)
            timeout: Timeout in seconds for this request
            callback: Optional callback(response_data, error_msg) on completion
            description: Human-readable description for logging

        Returns:
            True if request was created, False on error
        """
        # Auto-determine response type if not provided
        if response_type is None:
            response_type = RESPONSE_TYPE_MAP.get(request_type)
            if response_type is None:
                logger.warning(f"No response mapping for request type 0x{request_type:02X}")
                return False

        with self._lock:
            # Check if there's already a pending request with this SeqID
            if seq_id in self._pending_by_seq_id:
                existing = self._pending_by_seq_id[seq_id]
                if existing.is_pending:
                    logger.warning(
                        f"Request with SeqID 0x{seq_id:04X} already pending "
                        f"(created {existing.elapsed_seconds:.1f}s ago)"
                    )
                    return False

            request = TrackedRequest(
                seq_id=seq_id,
                request_type=request_type,
                response_type=response_type,
                timeout_seconds=timeout,
                callback=callback,
                description=description or f"seq=0x{seq_id:04X} 0x{request_type:02X}->0x{response_type:02X}"
            )
            self._pending_by_seq_id[seq_id] = request
            # Also track by response type for fallback
            self._pending_by_response[response_type] = request
            self._stats['requests_created'] += 1

            logger.debug(
                f"Created request: {description or ''} "
                f"seq=0x{seq_id:04X} req=0x{request_type:02X} -> resp=0x{response_type:02X} "
                f"timeout={timeout}s"
            )

            # Periodic cleanup
            self._maybe_cleanup()

            return True

    def complete_by_seq_id(self, seq_id: int, response_data: bytes) -> bool:
        """Complete a pending request by its SeqID (primary method).

        Called when a response message is received with a SeqID.

        Args:
            seq_id: The sequence ID from the response
            response_data: Response payload

        Returns:
            True if a pending request was completed
        """
        # Ignore broadcast SeqID
        if seq_id == 0:
            return False

        with self._lock:
            request = self._pending_by_seq_id.get(seq_id)
            if not request:
                logger.debug(f"No pending request for SeqID 0x{seq_id:04X}")
                return False

            if not request.is_pending:
                logger.debug(f"Request for SeqID 0x{seq_id:04X} already completed")
                return False

            request.state = RequestState.COMPLETED
            request.response_data = response_data
            request.event.set()
            self._stats['requests_completed'] += 1

            elapsed = request.elapsed_seconds
            logger.debug(
                f"Completed request {request.description} in {elapsed:.3f}s "
                f"({len(response_data)} bytes)"
            )

            # Remove from both tracking maps
            del self._pending_by_seq_id[seq_id]
            if request.response_type in self._pending_by_response:
                del self._pending_by_response[request.response_type]

            self._completed.append(request)
            if len(self._completed) > self._max_history:
                self._completed.pop(0)

            # Call callback if registered
            if request.callback:
                try:
                    request.callback(response_data, None)
                except Exception as e:
                    logger.error(f"Request callback error: {e}")

            return True

    def complete_by_response_type(self, response_type: int, response_data: bytes) -> bool:
        """Complete a pending request by its response type (fallback method).

        Called when a response message is received. Use complete_by_seq_id
        when SeqID is available (protocol v2).

        Args:
            response_type: The message type of the response received
            response_data: Response payload

        Returns:
            True if a pending request was completed
        """
        with self._lock:
            request = self._pending_by_response.get(response_type)
            if not request:
                # No pending request for this response type - that's OK for unsolicited messages
                return False

            if not request.is_pending:
                logger.debug(f"Request for 0x{response_type:02X} already completed")
                return False

            request.state = RequestState.COMPLETED
            request.response_data = response_data
            request.event.set()
            self._stats['requests_completed'] += 1

            elapsed = request.elapsed_seconds
            logger.debug(
                f"Completed request {request.description} in {elapsed:.3f}s "
                f"({len(response_data)} bytes)"
            )

            # Remove from both tracking maps
            del self._pending_by_response[response_type]
            if request.seq_id in self._pending_by_seq_id:
                del self._pending_by_seq_id[request.seq_id]

            self._completed.append(request)
            if len(self._completed) > self._max_history:
                self._completed.pop(0)

            # Call callback if registered
            if request.callback:
                try:
                    request.callback(response_data, None)
                except Exception as e:
                    logger.error(f"Request callback error: {e}")

            return True

    def fail_by_seq_id(self, seq_id: int, error_message: str) -> bool:
        """Mark a pending request as failed by SeqID.

        Args:
            seq_id: Sequence ID of the request
            error_message: Error description

        Returns:
            True if a pending request was marked failed
        """
        with self._lock:
            request = self._pending_by_seq_id.get(seq_id)
            if not request or not request.is_pending:
                return False

            request.state = RequestState.ERROR
            request.error_message = error_message
            request.event.set()
            self._stats['requests_error'] += 1

            logger.debug(f"Failed request {request.description}: {error_message}")

            # Remove from both tracking maps
            del self._pending_by_seq_id[seq_id]
            if request.response_type in self._pending_by_response:
                del self._pending_by_response[request.response_type]

            self._completed.append(request)

            if request.callback:
                try:
                    request.callback(None, error_message)
                except Exception as e:
                    logger.error(f"Request callback error: {e}")

            return True

    def fail_by_response_type(self, response_type: int, error_message: str) -> bool:
        """Mark a pending request as failed (fallback method).

        Args:
            response_type: Expected response type of the request
            error_message: Error description

        Returns:
            True if a pending request was marked failed
        """
        with self._lock:
            request = self._pending_by_response.get(response_type)
            if not request or not request.is_pending:
                return False

            request.state = RequestState.ERROR
            request.error_message = error_message
            request.event.set()
            self._stats['requests_error'] += 1

            logger.debug(f"Failed request {request.description}: {error_message}")

            # Remove from both tracking maps
            del self._pending_by_response[response_type]
            if request.seq_id in self._pending_by_seq_id:
                del self._pending_by_seq_id[request.seq_id]

            self._completed.append(request)

            if request.callback:
                try:
                    request.callback(None, error_message)
                except Exception as e:
                    logger.error(f"Request callback error: {e}")

            return True

    def wait_for_response_by_seq_id(self, seq_id: int, timeout: float = None) -> Optional[bytes]:
        """Wait for a response by SeqID and return response data (primary method).

        Args:
            seq_id: Sequence ID to wait for
            timeout: Override timeout (uses request's timeout if None)

        Returns:
            Response data bytes, or None if timeout/error
        """
        with self._lock:
            request = self._pending_by_seq_id.get(seq_id)
            if not request:
                logger.warning(f"wait_for_response_by_seq_id: No pending request for SeqID 0x{seq_id:04X}")
                return None

            wait_timeout = timeout if timeout is not None else request.timeout_seconds

        # Wait outside the lock
        if request.event.wait(wait_timeout):
            # Event was set - check result
            if request.state == RequestState.COMPLETED:
                return request.response_data
            else:
                logger.debug(f"Request for SeqID 0x{seq_id:04X} ended with state={request.state}")
                return None
        else:
            # Timeout
            with self._lock:
                if request.is_pending:
                    request.state = RequestState.TIMEOUT
                    self._stats['requests_timeout'] += 1
                    # Remove from both tracking maps
                    if seq_id in self._pending_by_seq_id:
                        del self._pending_by_seq_id[seq_id]
                    if request.response_type in self._pending_by_response:
                        del self._pending_by_response[request.response_type]
                    self._completed.append(request)

            logger.warning(f"Request {request.description} timed out after {wait_timeout}s")
            return None

    def wait_for_response(self, response_type: int, timeout: float = None) -> Optional[bytes]:
        """Wait for a response by response type and return response data (fallback).

        Args:
            response_type: Response type to wait for
            timeout: Override timeout (uses request's timeout if None)

        Returns:
            Response data bytes, or None if timeout/error
        """
        with self._lock:
            request = self._pending_by_response.get(response_type)
            if not request:
                logger.warning(f"wait_for_response: No pending request for 0x{response_type:02X}")
                return None

            wait_timeout = timeout if timeout is not None else request.timeout_seconds

        # Wait outside the lock
        if request.event.wait(wait_timeout):
            # Event was set - check result
            if request.state == RequestState.COMPLETED:
                return request.response_data
            else:
                logger.debug(f"Request for 0x{response_type:02X} ended with state={request.state}")
                return None
        else:
            # Timeout
            with self._lock:
                if request.is_pending:
                    request.state = RequestState.TIMEOUT
                    self._stats['requests_timeout'] += 1
                    # Remove from both tracking maps
                    if response_type in self._pending_by_response:
                        del self._pending_by_response[response_type]
                    if request.seq_id in self._pending_by_seq_id:
                        del self._pending_by_seq_id[request.seq_id]
                    self._completed.append(request)

            logger.warning(f"Request {request.description} timed out after {wait_timeout}s")
            return None

    def cancel_by_seq_id(self, seq_id: int) -> bool:
        """Cancel a pending request by SeqID (primary method).

        Args:
            seq_id: Sequence ID of the request to cancel

        Returns:
            True if request was cancelled
        """
        with self._lock:
            request = self._pending_by_seq_id.get(seq_id)
            if not request or not request.is_pending:
                return False

            request.state = RequestState.CANCELLED
            request.event.set()
            self._stats['requests_cancelled'] += 1

            # Remove from both tracking maps
            del self._pending_by_seq_id[seq_id]
            if request.response_type in self._pending_by_response:
                del self._pending_by_response[request.response_type]

            logger.debug(f"Cancelled request {request.description}")
            return True

    def cancel_by_response_type(self, response_type: int) -> bool:
        """Cancel a pending request by response type (fallback method).

        Args:
            response_type: Expected response type to cancel

        Returns:
            True if request was cancelled
        """
        with self._lock:
            request = self._pending_by_response.get(response_type)
            if not request or not request.is_pending:
                return False

            request.state = RequestState.CANCELLED
            request.event.set()
            self._stats['requests_cancelled'] += 1

            # Remove from both tracking maps
            del self._pending_by_response[response_type]
            if request.seq_id in self._pending_by_seq_id:
                del self._pending_by_seq_id[request.seq_id]

            logger.debug(f"Cancelled request {request.description}")
            return True

    def cancel_all(self):
        """Cancel all pending requests."""
        with self._lock:
            # Use _pending_by_seq_id as primary (contains all requests)
            count = 0
            for seq_id, request in list(self._pending_by_seq_id.items()):
                if request.is_pending:
                    request.state = RequestState.CANCELLED
                    request.event.set()
                    self._stats['requests_cancelled'] += 1
                    count += 1
            # Clear both tracking maps
            self._pending_by_seq_id.clear()
            self._pending_by_response.clear()
            if count > 0:
                logger.debug(f"Cancelled {count} pending requests")

    def is_pending_by_seq_id(self, seq_id: int) -> bool:
        """Check if there's a pending request for a SeqID (primary method)."""
        with self._lock:
            request = self._pending_by_seq_id.get(seq_id)
            return request is not None and request.is_pending

    def is_pending(self, response_type: int) -> bool:
        """Check if there's a pending request for a response type (fallback)."""
        with self._lock:
            request = self._pending_by_response.get(response_type)
            return request is not None and request.is_pending

    def get_pending_count(self) -> int:
        """Get number of pending requests."""
        with self._lock:
            # Use primary map for counting
            return sum(1 for r in self._pending_by_seq_id.values() if r.is_pending)

    def get_pending_seq_ids(self) -> List[int]:
        """Get list of pending SeqIDs (primary method)."""
        with self._lock:
            return [
                seq_id for seq_id, r in self._pending_by_seq_id.items()
                if r.is_pending
            ]

    def get_pending_types(self) -> List[int]:
        """Get list of pending response types (fallback method)."""
        with self._lock:
            return [
                rt for rt, r in self._pending_by_response.items()
                if r.is_pending
            ]

    def get_stats(self) -> Dict[str, int]:
        """Get request statistics."""
        with self._lock:
            stats = self._stats.copy()
            stats['pending'] = self.get_pending_count()
            return stats

    def _maybe_cleanup(self):
        """Periodically clean up expired requests."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        expired_seq_ids = []

        with self._lock:
            # Use _pending_by_seq_id as primary for cleanup
            for seq_id, request in list(self._pending_by_seq_id.items()):
                if request.is_expired:
                    request.state = RequestState.TIMEOUT
                    request.event.set()
                    self._stats['requests_timeout'] += 1
                    expired_seq_ids.append((seq_id, request.response_type))
                    self._completed.append(request)

            # Remove from both maps
            for seq_id, response_type in expired_seq_ids:
                if seq_id in self._pending_by_seq_id:
                    del self._pending_by_seq_id[seq_id]
                if response_type in self._pending_by_response:
                    del self._pending_by_response[response_type]

            # Trim history
            while len(self._completed) > self._max_history:
                self._completed.pop(0)

        if expired_seq_ids:
            logger.debug(f"Cleaned up {len(expired_seq_ids)} expired requests")
