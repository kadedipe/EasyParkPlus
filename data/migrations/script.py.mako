# parking-management/data/migrations/script.py.mako

"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}


# Custom methods for data quality checks
def validate_vehicle_data():
    """Validate vehicle data quality after migration"""
    from parking_management.data.migrations import VehicleDataQualityMigration
    import os
    
    # Get Elasticsearch config from environment
    es_host = os.getenv('ES_HOST', 'localhost')
    es_port = int(os.getenv('ES_PORT', 9200))
    es_user = os.getenv('ES_USER')
    es_pass = os.getenv('ES_PASS')
    
    auth = (es_user, es_pass) if es_user and es_pass else None
    
    migration = VehicleDataQualityMigration(
        es_host=es_host,
        es_port=es_port,
        auth=auth
    )
    
    results = migration.run_quality_check()
    
    # Check quality thresholds
    quality_score = results.get('quality_score', 0)
    if quality_score < 90:
        raise Exception(f"Vehicle data quality score ({quality_score}%) below threshold (90%)")
    
    return results