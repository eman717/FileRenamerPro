"""
Timer Manager for File Renamer Pro
Handles clock in/out functionality and time logging
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class TimeLogEntry:
    """A single time log entry"""
    job_number: str
    job_folder: Optional[str]
    clock_in: str  # ISO format
    clock_out: str  # ISO format
    duration_minutes: float
    date: str
    files_renamed: int = 0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimeLogEntry':
        return cls(
            job_number=data.get('job_number', ''),
            job_folder=data.get('job_folder'),
            clock_in=data.get('clock_in', ''),
            clock_out=data.get('clock_out', ''),
            duration_minutes=data.get('duration_minutes', 0),
            date=data.get('date', ''),
            files_renamed=data.get('files_renamed', 0),
            notes=data.get('notes', ''),
        )


class TimerManager:
    """Manages the clock in/out timer functionality"""

    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self._ensure_log_dir()
        
        self.is_clocked_in: bool = False
        self.clock_in_time: Optional[datetime] = None
        self.current_job: Optional[str] = None
        self.current_job_folder: Optional[str] = None
        self.files_renamed: int = 0

    def _ensure_log_dir(self) -> None:
        """Ensure log directory exists"""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            logger.error(f"Cannot create log directory: {e}")
        except Exception as e:
            logger.error(f"Error creating log directory: {e}")

    def clock_in(self, job_number: str, job_folder: Optional[str] = None) -> tuple[bool, str]:
        """
        Clock in to start tracking time.
        
        Args:
            job_number: The job number to track
            job_folder: Optional full path to job folder
            
        Returns:
            Tuple of (success, message)
        """
        if self.is_clocked_in:
            logger.warning("Attempted to clock in while already clocked in")
            return False, "Already clocked in!"

        if not job_number:
            return False, "Job number is required"

        self.is_clocked_in = True
        self.clock_in_time = datetime.now()
        self.current_job = job_number
        self.current_job_folder = job_folder
        self.files_renamed = 0

        time_str = self.clock_in_time.strftime('%I:%M %p')
        logger.info(f"Clocked in to job {job_number} at {time_str}")
        return True, f"Clocked in at {time_str}"

    def clock_out(self, notes: str = "") -> tuple[bool, str, Optional[TimeLogEntry]]:
        """
        Clock out and save the time log entry.
        
        Args:
            notes: Optional notes for this session
            
        Returns:
            Tuple of (success, message, log_entry)
        """
        if not self.is_clocked_in:
            logger.warning("Attempted to clock out while not clocked in")
            return False, "Not clocked in!", None

        if self.clock_in_time is None:
            logger.error("Clock in time is None despite being clocked in")
            self.is_clocked_in = False
            return False, "Invalid state - clock in time missing", None

        clock_out_time = datetime.now()
        duration = clock_out_time - self.clock_in_time
        duration_minutes = round(duration.total_seconds() / 60, 2)

        # Create log entry
        log_entry = TimeLogEntry(
            job_number=self.current_job or "",
            job_folder=self.current_job_folder,
            clock_in=self.clock_in_time.isoformat(),
            clock_out=clock_out_time.isoformat(),
            duration_minutes=duration_minutes,
            date=self.clock_in_time.strftime("%Y-%m-%d"),
            files_renamed=self.files_renamed,
            notes=notes,
        )

        # Save to file
        self._save_log_entry(log_entry)

        # Format duration string
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Reset state
        self.is_clocked_in = False
        self.clock_in_time = None
        job_number = self.current_job
        self.current_job = None
        self.current_job_folder = None

        logger.info(f"Clocked out from job {job_number}. Duration: {duration_str}")
        return True, f"Clocked out! Session: {duration_str}", log_entry

    def _save_log_entry(self, entry: TimeLogEntry) -> bool:
        """Save a log entry to the daily log file"""
        log_file = self.log_dir / f"timelog_{entry.date}.json"
        entries: List[Dict[str, Any]] = []

        # Load existing entries
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Corrupted log file {log_file}: {e}")
                # Backup corrupted file
                backup_path = log_file.with_suffix('.json.bak')
                log_file.rename(backup_path)
                entries = []
            except Exception as e:
                logger.error(f"Error reading log file: {e}")
                entries = []

        # Add new entry
        entries.append(entry.to_dict())

        # Save
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(entries, f, indent=2)
            logger.debug(f"Saved log entry to {log_file}")
            return True
        except PermissionError as e:
            logger.error(f"Permission denied writing log: {e}")
        except Exception as e:
            logger.error(f"Error saving log entry: {e}")
        return False

    def increment_files_renamed(self, count: int = 1) -> None:
        """Increment the files renamed counter"""
        self.files_renamed += count

    def get_elapsed_time(self) -> str:
        """Get elapsed time as formatted string HH:MM:SS"""
        if not self.is_clocked_in or not self.clock_in_time:
            return "00:00:00"
        
        elapsed = datetime.now() - self.clock_in_time
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_elapsed_seconds(self) -> float:
        """Get elapsed time in seconds"""
        if not self.is_clocked_in or not self.clock_in_time:
            return 0.0
        return (datetime.now() - self.clock_in_time).total_seconds()

    def get_today_entries(self) -> List[TimeLogEntry]:
        """Get all log entries for today"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_entries_for_date(today)

    def get_entries_for_date(self, date_str: str) -> List[TimeLogEntry]:
        """Get all log entries for a specific date"""
        log_file = self.log_dir / f"timelog_{date_str}.json"
        
        if not log_file.exists():
            return []

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [TimeLogEntry.from_dict(entry) for entry in data]
        except Exception as e:
            logger.error(f"Error reading log entries: {e}")
            return []

    def get_total_time_today(self) -> float:
        """Get total time worked today in minutes"""
        entries = self.get_today_entries()
        return sum(entry.duration_minutes for entry in entries)
