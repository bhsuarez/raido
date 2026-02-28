#!/usr/bin/env python3
"""
Sync stations from stations.yml to the database

This script ensures the database stations table matches the configuration
in stations.yml. It will create, update, or deactivate stations as needed.

Usage:
    python scripts/sync-stations-db.py
"""

import yaml
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "api"))

from app.core.database import AsyncSessionLocal
from app.models import Station, Setting
from sqlalchemy import select

async def load_stations_config():
    """Load stations configuration from stations.yml"""
    config_path = Path(__file__).parent.parent / "stations.yml"

    if not config_path.exists():
        print(f"❌ Error: {config_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)

async def sync_stations():
    """Sync stations from config to database"""
    print("🎵 Raido Station Database Sync")
    print("=" * 50)

    # Load configuration
    print("📖 Loading stations.yml...")
    config = await load_stations_config()
    config_stations = config['stations']

    print(f"✅ Found {len(config_stations)} stations in config")

    async with AsyncSessionLocal() as db:
        # Get existing stations from database
        result = await db.execute(select(Station))
        existing_stations = {s.identifier: s for s in result.scalars().all()}

        print(f"📊 Found {len(existing_stations)} stations in database")

        created = 0
        updated = 0
        deactivated = 0

        # Process each station from config
        for station_id, station_config in config_stations.items():
            if station_id in existing_stations:
                # Update existing station
                station = existing_stations[station_id]
                station.name = station_config['display_name']
                station.description = station_config.get('description')
                station.is_active = True
                station.updated_at = datetime.now(timezone.utc)
                print(f"  ✏️  Updated: {station_id} ({station.name})")
                updated += 1
            else:
                # Create new station
                station = Station(
                    identifier=station_id,
                    name=station_config['display_name'],
                    description=station_config.get('description'),
                    is_active=True
                )
                db.add(station)
                print(f"  ➕ Created: {station_id} ({station.name})")
                created += 1

            # Sync default settings for this station
            await sync_station_settings(db, station_id, station_config)

        # Deactivate stations not in config
        for db_station_id, db_station in existing_stations.items():
            if db_station_id not in config_stations:
                db_station.is_active = False
                db_station.updated_at = datetime.now(timezone.utc)
                print(f"  ⏸️  Deactivated: {db_station_id} ({db_station.name})")
                deactivated += 1

        await db.commit()

        print("\n📊 Summary:")
        print(f"  Created: {created}")
        print(f"  Updated: {updated}")
        print(f"  Deactivated: {deactivated}")
        print("\n✅ Database sync complete!")

async def sync_station_settings(db, station_id: str, station_config: dict):
    """Sync default settings for a station"""
    dj_config = station_config.get('dj_worker', {})

    # Define settings to sync
    settings_to_sync = {
        'dj_provider': dj_config.get('default_provider', 'templates'),
        'dj_voice_provider': dj_config.get('default_voice_provider', 'kokoro'),
        'dj_commentary_interval': dj_config.get('commentary_interval', 1),
        'dj_max_seconds': dj_config.get('max_seconds', 30),
    }

    # Add voice setting based on provider
    voice_provider = dj_config.get('default_voice_provider', 'kokoro')
    default_voice = dj_config.get('default_voice')

    if default_voice:
        if voice_provider == 'kokoro':
            settings_to_sync['kokoro_voice'] = default_voice
        elif voice_provider == 'chatterbox':
            settings_to_sync['chatterbox_voice'] = default_voice

    # Add custom prompt template if provided
    if 'prompt_template' in dj_config:
        settings_to_sync['dj_prompt_template'] = dj_config['prompt_template'].strip()

    # Check and create/update settings
    for key, value in settings_to_sync.items():
        result = await db.execute(
            select(Setting).where(Setting.key == key, Setting.station == station_id)
        )
        setting = result.scalar_one_or_none()

        if not setting:
            # Infer value type
            if isinstance(value, bool):
                value_type = 'bool'
            elif isinstance(value, int):
                value_type = 'int'
            elif isinstance(value, float):
                value_type = 'float'
            else:
                value_type = 'string'

            setting = Setting(
                key=key,
                value=str(value),
                value_type=value_type,
                station=station_id
            )
            db.add(setting)

if __name__ == '__main__':
    asyncio.run(sync_stations())
