"""
Configuration management for File Renamer Pro
Handles loading, saving, and validating configuration
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class TimerSettings:
    """Timer configuration settings"""
    warning_minutes: int = 30
    reminder_interval_minutes: int = 15
    auto_save_log: bool = True


@dataclass
class JobFolderSettings:
    """Job folder configuration settings"""
    base_directory: str = ""
    job_number_pattern: str = r"^(\d+)"
    recent_folders: List[str] = field(default_factory=list)
    max_recent: int = 10


@dataclass
class DuplicateHandling:
    """Settings for handling duplicate files"""
    mode: str = "ask"  # ask, skip, increment, overwrite
    auto_increment_format: str = "_{n}"


@dataclass
class Config:
    """Main configuration class"""
    product_skus: List[str] = field(default_factory=lambda: ["-- Select SKU --", "CUSTOM"])
    production_types: List[str] = field(default_factory=lambda: [
        "PRINT", "CUTFILE", "SUBLIMATION", "DTF", "EMBROIDERY", "LASER"
    ])
    file_purposes: List[str] = field(default_factory=lambda: [
        "PROOF", "PRINT", "WEB", "SOURCE", "MOCKUP", "CUTFILE", "PREVIEW"
    ])
    revisions: List[str] = field(default_factory=lambda: ["1", "2", "3", "4", "5", "FINAL"])
    timer_settings: TimerSettings = field(default_factory=TimerSettings)
    job_folder_settings: JobFolderSettings = field(default_factory=JobFolderSettings)
    duplicate_handling: DuplicateHandling = field(default_factory=DuplicateHandling)
    log_directory: str = "time_logs"
    backup_before_rename: bool = False
    show_tooltips: bool = True
    confirm_before_rename: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for JSON serialization"""
        return {
            'product_skus': self.product_skus,
            'production_types': self.production_types,
            'file_purposes': self.file_purposes,
            'revisions': self.revisions,
            'timer_settings': asdict(self.timer_settings),
            'job_folder_settings': {
                **asdict(self.job_folder_settings),
            },
            'duplicate_handling': asdict(self.duplicate_handling),
            'log_directory': self.log_directory,
            'backup_before_rename': self.backup_before_rename,
            'show_tooltips': self.show_tooltips,
            'confirm_before_rename': self.confirm_before_rename,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary"""
        timer_data = data.get('timer_settings', {})
        job_data = data.get('job_folder_settings', {})
        dup_data = data.get('duplicate_handling', {})

        return cls(
            product_skus=data.get('product_skus', cls().product_skus),
            production_types=data.get('production_types', cls().production_types),
            file_purposes=data.get('file_purposes', cls().file_purposes),
            revisions=data.get('revisions', cls().revisions),
            timer_settings=TimerSettings(
                warning_minutes=timer_data.get('warning_minutes', 30),
                reminder_interval_minutes=timer_data.get('reminder_interval_minutes', 15),
                auto_save_log=timer_data.get('auto_save_log', True),
            ),
            job_folder_settings=JobFolderSettings(
                base_directory=job_data.get('base_directory', ''),
                job_number_pattern=job_data.get('job_number_pattern', r'^(\d+)'),
                recent_folders=job_data.get('recent_folders', []),
                max_recent=job_data.get('max_recent', 10),
            ),
            duplicate_handling=DuplicateHandling(
                mode=dup_data.get('mode', 'ask'),
                auto_increment_format=dup_data.get('auto_increment_format', '_{n}'),
            ),
            log_directory=data.get('log_directory', 'time_logs'),
            backup_before_rename=data.get('backup_before_rename', False),
            show_tooltips=data.get('show_tooltips', True),
            confirm_before_rename=data.get('confirm_before_rename', True),
        )

    def add_recent_folder(self, folder_path: str) -> None:
        """Add a folder to recent folders list"""
        recent = self.job_folder_settings.recent_folders
        if folder_path in recent:
            recent.remove(folder_path)
        recent.insert(0, folder_path)
        # Trim to max
        max_recent = self.job_folder_settings.max_recent
        self.job_folder_settings.recent_folders = recent[:max_recent]


def load_config(config_path: Path) -> Config:
    """Load configuration from JSON file"""
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded config from {config_path}")
                return Config.from_dict(data)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
    except PermissionError as e:
        logger.error(f"Permission denied reading config: {e}")
    except Exception as e:
        logger.error(f"Error loading config: {e}")

    logger.info("Using default configuration")
    return Config()


def save_config(config: Config, config_path: Path) -> bool:
    """Save configuration to JSON file"""
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2)
        logger.info(f"Saved config to {config_path}")
        return True
    except PermissionError as e:
        logger.error(f"Permission denied writing config: {e}")
    except Exception as e:
        logger.error(f"Error saving config: {e}")
    return False
