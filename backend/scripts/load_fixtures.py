#!/usr/bin/env python3
"""
Script to load fixtures into the database.
Run with: python -m scripts.load_fixtures
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from data.fixtures import (
    load_all_fixtures,
    get_loading_order,
    FIXTURE_FILES,
    load_fixture,
)
from database import get_db
from models import (
    User,
    Vehicle,
    ParkingSpot,
    Reservation,
    Payment,
    Notification,
    Review,
    WaitlistEntry,
    MaintenanceRecord,
    PriceRule,
    Discount,
    LoyaltyProgram,
    AuditLog,
)
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mapping of fixture names to model classes
MODEL_MAP = {
    'users': User,
    'vehicles': Vehicle,
    'parking_spots': ParkingSpot,
    'reservations': Reservation,
    'payments': Payment,
    'notifications': Notification,
    'reviews': Review,
    'waitlist': WaitlistEntry,
    'maintenance': MaintenanceRecord,
    'price_rules': PriceRule,
    'discounts': Discount,
    'loyalty_programs': LoyaltyProgram,
    'audit_logs': AuditLog,
}


async def clear_table(session: AsyncSession, model):
    """Clear all records from a table."""
    logger.info(f"Clearing table {model.__tablename__}...")
    await session.execute(model.__table__.delete())
    await session.commit()


async def load_fixture_data(session: AsyncSession, fixture_name: str, data: list):
    """Load fixture data into the database."""
    model = MODEL_MAP.get(fixture_name)
    if not model:
        logger.warning(f"No model mapping for fixture: {fixture_name}")
        return 0
    
    logger.info(f"Loading {len(data)} records into {model.__tablename__}...")
    
    count = 0
    for record in data:
        # Convert string dates to datetime objects if needed
        for key, value in record.items():
            if isinstance(value, str) and 'T' in value and ('Z' in value or '+' in value):
                from datetime import datetime
                try:
                    record[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    pass
        
        instance = model(**record)
        session.add(instance)
        count += 1
    
    await session.commit()
    logger.info(f"✅ Loaded {count} records into {model.__tablename__}")
    return count


async def main():
    """Main function to load all fixtures."""
    logger.info("=" * 50)
    logger.info("Loading fixtures into database")
    logger.info("=" * 50)
    
    # Get loading order based on dependencies
    loading_order = get_loading_order()
    logger.info(f"Loading order: {', '.join(loading_order)}")
    
    # Load all fixture data
    fixtures = load_all_fixtures()
    
    # Get database session
    async for session in get_db():
        try:
            total_records = 0
            
            # Load fixtures in order
            for fixture_name in loading_order:
                if fixture_name not in fixtures:
                    continue
                
                data = fixtures[fixture_name]
                if not data:
                    continue
                
                # Clear existing data (optional - comment out if not wanted)
                # await clear_table(session, MODEL_MAP[fixture_name])
                
                # Load new data
                count = await load_fixture_data(session, fixture_name, data)
                total_records += count
            
            logger.info("=" * 50)
            logger.info(f"✅ Successfully loaded {total_records} total records")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"Error loading fixtures: {e}")
            await session.rollback()
            raise
        
        break  # Only use one session


if __name__ == '__main__':
    asyncio.run(main())