"""
Management command: backup_db

Creates a timestamped copy of the SQLite database in backups/db/.
Keeps only the last N backups (default 30).

Usage:
    python manage.py backup_db
    python manage.py backup_db --keep 10
"""
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Back up the SQLite database to backups/db/'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep', type=int, default=30,
            help='Number of backups to keep (default: 30)',
        )

    def handle(self, *args, **options):
        db_path = Path(settings.DATABASES['default'].get('NAME', ''))
        if not db_path.exists():
            self.stderr.write(self.style.ERROR(f'Database file not found: {db_path}'))
            return

        backup_dir = settings.BASE_DIR / 'backups' / 'db'
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = backup_dir / f'db_{timestamp}.sqlite3'
        shutil.copy2(db_path, dest)
        self.stdout.write(self.style.SUCCESS(f'Backup saved: {dest}'))

        keep = options['keep']
        backups = sorted(backup_dir.glob('db_*.sqlite3'))
        for old in backups[:-keep]:
            old.unlink()
            self.stdout.write(f'Removed old backup: {old.name}')
