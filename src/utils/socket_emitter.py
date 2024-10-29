# src/utils/socket_emitter.py

from typing import Dict, Any, Optional
from flask_socketio import SocketIO

class ParsingProgressEmitter:
    """
    Handles socket event emissions for real-time parsing progress updates.
    """
    
    def __init__(self, socketio: SocketIO, sid: str):
        self.socketio = socketio
        self.sid = sid
        self.current_line = 0
        self.total_lines = 0
    
    def emit_line_parsed(
        self,
        content: str,
        section: str,
        confidence: Optional[float] = None
    ) -> None:
        """
        Emit a line_parsed event with the parsed content and section.
        
        Args:
            content: The parsed content
            section: The section being parsed (e.g., "Requesting Party")
            confidence: Optional confidence score for the parsed content
        """
        self.current_line += 1
        data = {
            'line_number': self.current_line,
            'parsed_content': content,
            'highlight_section': section
        }
        if confidence is not None:
            data['confidence'] = confidence
            
        self.socketio.emit('line_parsed', data, room=self.sid)
        
        # Update progress
        if self.total_lines > 0:
            progress = min(95, int((self.current_line / self.total_lines) * 100))
            self.emit_progress(progress)
    
    def emit_progress(self, progress: int) -> None:
        """
        Emit a parsing_progress event with the current progress percentage.
        
        Args:
            progress: Progress percentage (0-100)
        """
        self.socketio.emit(
            'parsing_progress',
            {'progress': progress},
            room=self.sid
        )
    
    def emit_parsing_started(self, total_lines: int) -> None:
        """
        Emit a parsing_started event with the total number of lines to parse.
        
        Args:
            total_lines: Total number of lines in the content
        """
        self.total_lines = total_lines
        self.current_line = 0
        self.socketio.emit(
            'parsing_started',
            {'total_lines': total_lines},
            room=self.sid
        )
    
    def emit_section_complete(self, section: str, metadata: Dict[str, Any]) -> None:
        """
        Emit a section_complete event with section metadata.
        
        Args:
            section: The completed section name
            metadata: Additional metadata about the section parsing
        """
        self.socketio.emit(
            'section_complete',
            {
                'section': section,
                'metadata': metadata
            },
            room=self.sid
        )
    
    def emit_parsing_error(self, error: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit a parsing_error event with error details.
        
        Args:
            error: The error message
            details: Optional additional error details
        """
        data = {'error': error}
        if details:
            data['details'] = details
        self.socketio.emit('parsing_error', data, room=self.sid)
    
    def emit_parsing_complete(self, metadata: Dict[str, Any]) -> None:
        """
        Emit a parsing_completed event with parsing metadata.
        
        Args:
            metadata: Metadata about the completed parsing operation
        """
        self.socketio.emit(
            'parsing_completed',
            {'metadata': metadata},
            room=self.sid
        )