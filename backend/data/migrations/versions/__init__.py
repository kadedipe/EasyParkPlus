# parking-management/data/migrations/versions/__init__.py
"""
Alembic migration versions package.

This package contains all database migration versions for the parking management system.
Each migration file represents a specific version of the database schema and data.
"""

import os
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import importlib.util
import logging

# Version package metadata
__version__ = "1.0.0"
__all__ = [
    'get_current_version',
    'get_version_history',
    'get_migration_by_revision',
    'get_migrations_by_date',
    'validate_migrations',
    'get_latest_migration',
    'get_migration_dependencies',
    'MigrationInfo'
]

logger = logging.getLogger(__name__)


class MigrationInfo:
    """
    Container for migration version information
    """
    
    def __init__(self, revision: str, down_revision: Optional[str], 
                 description: str, filename: str, create_date: datetime):
        """
        Initialize migration info
        
        Args:
            revision: Revision ID
            down_revision: Previous revision ID
            description: Migration description
            filename: Migration filename
            create_date: Creation timestamp
        """
        self.revision = revision
        self.down_revision = down_revision
        self.description = description
        self.filename = filename
        self.create_date = create_date
        self.is_head = False
        self.is_base = False
        self.dependencies = []
    
    @property
    def is_merge(self) -> bool:
        """Check if this is a merge migration"""
        return isinstance(self.down_revision, (list, tuple)) and len(self.down_revision) > 1
    
    @property
    def revision_short(self) -> str:
        """Get short revision ID (first 8 characters)"""
        return self.revision[:8] if self.revision else ""
    
    def __repr__(self) -> str:
        return f"<Migration {self.revision_short}: {self.description}>"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'revision': self.revision,
            'revision_short': self.revision_short,
            'down_revision': self.down_revision,
            'description': self.description,
            'filename': self.filename,
            'create_date': self.create_date.isoformat() if self.create_date else None,
            'is_head': self.is_head,
            'is_base': self.is_base,
            'is_merge': self.is_merge,
            'dependencies': self.dependencies
        }


def _get_version_files() -> List[str]:
    """
    Get all migration version files in the versions directory
    
    Returns:
        List of Python file paths
    """
    version_dir = os.path.dirname(os.path.abspath(__file__))
    files = []
    
    for f in os.listdir(version_dir):
        if f.endswith('.py') and f != '__init__.py':
            files.append(os.path.join(version_dir, f))
    
    return sorted(files)


def _parse_migration_file(filepath: str) -> Optional[MigrationInfo]:
    """
    Parse a migration file to extract metadata
    
    Args:
        filepath: Path to migration file
        
    Returns:
        MigrationInfo object or None if parsing fails
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract revision ID
        revision_match = re.search(r'revision:\s*=\s*[\'"]([a-f0-9]+)[\'"]', content)
        if not revision_match:
            logger.warning(f"Could not find revision in {filepath}")
            return None
        
        revision = revision_match.group(1)
        
        # Extract down revision
        down_match = re.search(r'down_revision:\s*=\s*[\'"]([a-f0-9]+)[\'"]', content)
        down_revision = down_match.group(1) if down_match else None
        
        # Handle list of down revisions (merge migrations)
        if not down_match:
            list_match = re.search(r'down_revision:\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if list_match:
                # Extract revision IDs from list
                revs = re.findall(r'[\'"]([a-f0-9]+)[\'"]', list_match.group(1))
                down_revision = revs if revs else None
        
        # Extract description
        desc_match = re.search(r'"""(.+?)"""', content, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else "No description"
        # Take first line only
        description = description.split('\n')[0].strip()
        
        # Extract create date
        date_match = re.search(r'Create Date:\s*(.+)', content)
        create_date = None
        if date_match:
            try:
                date_str = date_match.group(1).strip()
                # Parse various date formats
                for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                    try:
                        create_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
            except Exception as e:
                logger.debug(f"Could not parse date in {filepath}: {e}")
        
        # Get filename
        filename = os.path.basename(filepath)
        
        return MigrationInfo(
            revision=revision,
            down_revision=down_revision,
            description=description,
            filename=filename,
            create_date=create_date or datetime.fromtimestamp(os.path.getctime(filepath))
        )
        
    except Exception as e:
        logger.error(f"Error parsing migration file {filepath}: {e}")
        return None


def get_all_migrations() -> List[MigrationInfo]:
    """
    Get all migrations in the versions directory
    
    Returns:
        List of MigrationInfo objects
    """
    migrations = []
    files = _get_version_files()
    
    for filepath in files:
        migration = _parse_migration_file(filepath)
        if migration:
            migrations.append(migration)
    
    # Sort by creation date
    migrations.sort(key=lambda x: x.create_date)
    
    # Identify heads and bases
    revisions = {m.revision: m for m in migrations}
    
    for migration in migrations:
        # Check if this is a head (no migrations depend on it)
        is_head = True
        for other in migrations:
            if other.down_revision:
                if isinstance(other.down_revision, list):
                    if migration.revision in other.down_revision:
                        is_head = False
                        break
                elif other.down_revision == migration.revision:
                    is_head = False
                    break
        migration.is_head = is_head
        
        # Check if this is a base (no down_revision)
        migration.is_base = migration.down_revision is None
        
        # Get dependencies
        if migration.down_revision:
            if isinstance(migration.down_revision, list):
                migration.dependencies = [
                    revisions[rev] for rev in migration.down_revision 
                    if rev in revisions
                ]
            else:
                if migration.down_revision in revisions:
                    migration.dependencies = [revisions[migration.down_revision]]
    
    return migrations


def get_current_version() -> Optional[str]:
    """
    Get the current migration version from the database
    This requires a database connection and will be implemented
    when the database is set up.
    
    Returns:
        Current revision ID or None if not available
    """
    # This is a placeholder - actual implementation would query the database
    # from alembic import command
    # from alembic.config import Config
    # alembic_cfg = Config("alembic.ini")
    # return command.current(alembic_cfg)
    
    logger.warning("get_current_version() requires database connection - returning None")
    return None


def get_version_history() -> List[Dict]:
    """
    Get the complete version history
    
    Returns:
        List of migration information dictionaries
    """
    migrations = get_all_migrations()
    return [m.to_dict() for m in migrations]


def get_migration_by_revision(revision: str) -> Optional[MigrationInfo]:
    """
    Get migration by revision ID
    
    Args:
        revision: Revision ID (full or short)
        
    Returns:
        MigrationInfo object or None if not found
    """
    migrations = get_all_migrations()
    
    # Try exact match first
    for m in migrations:
        if m.revision == revision:
            return m
    
    # Try short revision match
    for m in migrations:
        if m.revision_short == revision[:8]:
            return m
    
    return None


def get_migrations_by_date(start_date: datetime, end_date: Optional[datetime] = None) -> List[MigrationInfo]:
    """
    Get migrations created within a date range
    
    Args:
        start_date: Start date
        end_date: End date (defaults to now)
        
    Returns:
        List of MigrationInfo objects
    """
    if end_date is None:
        end_date = datetime.now()
    
    migrations = get_all_migrations()
    
    return [
        m for m in migrations 
        if start_date <= m.create_date <= end_date
    ]


def validate_migrations() -> Tuple[bool, List[str]]:
    """
    Validate migration chain integrity
    
    Returns:
        Tuple of (is_valid, list of issues)
    """
    migrations = get_all_migrations()
    issues = []
    
    if not migrations:
        issues.append("No migrations found")
        return False, issues
    
    # Build revision map
    revision_map = {m.revision: m for m in migrations}
    
    # Check for circular dependencies
    visited = set()
    path = []
    
    def check_circular(revision, path):
        if revision in path:
            issues.append(f"Circular dependency detected: {' -> '.join(path + [revision])}")
            return True
        
        if revision in visited:
            return False
        
        visited.add(revision)
        path.append(revision)
        
        migration = revision_map.get(revision)
        if migration and migration.down_revision:
            if isinstance(migration.down_revision, list):
                for dep in migration.down_revision:
                    if dep in revision_map:
                        if check_circular(dep, path.copy()):
                            return True
                    else:
                        issues.append(f"Missing dependency: {dep} referenced by {revision}")
            else:
                if migration.down_revision in revision_map:
                    if check_circular(migration.down_revision, path.copy()):
                        return True
                else:
                    issues.append(f"Missing dependency: {migration.down_revision} referenced by {revision}")
        
        return False
    
    # Check each head
    heads = [m for m in migrations if m.is_head]
    for head in heads:
        if check_circular(head.revision, []):
            return False, issues
    
    # Check for multiple heads (unless intentional)
    if len(heads) > 1:
        issues.append(f"Multiple migration heads detected: {[h.revision_short for h in heads]}")
    
    # Check for gaps in lineage
    for migration in migrations:
        if migration.down_revision and not migration.is_base:
            if isinstance(migration.down_revision, list):
                missing = [rev for rev in migration.down_revision if rev not in revision_map]
                if missing:
                    issues.append(f"Migration {migration.revision_short} has missing dependencies: {missing}")
            else:
                if migration.down_revision not in revision_map:
                    issues.append(f"Migration {migration.revision_short} references missing revision {migration.down_revision}")
    
    return len(issues) == 0, issues


def get_latest_migration() -> Optional[MigrationInfo]:
    """
    Get the latest migration (by creation date)
    
    Returns:
        Latest MigrationInfo or None
    """
    migrations = get_all_migrations()
    if migrations:
        return migrations[-1]
    return None


def get_migration_dependencies(revision: str) -> List[MigrationInfo]:
    """
    Get all dependencies for a migration
    
    Args:
        revision: Revision ID
        
    Returns:
        List of dependency migrations
    """
    migration = get_migration_by_revision(revision)
    if not migration:
        return []
    
    dependencies = []
    to_process = migration.dependencies.copy()
    processed = set()
    
    while to_process:
        current = to_process.pop(0)
        if current.revision not in processed:
            dependencies.append(current)
            processed.add(current.revision)
            to_process.extend(current.dependencies)
    
    return dependencies


def get_migration_chain(start_revision: Optional[str] = None, 
                       end_revision: Optional[str] = None) -> List[MigrationInfo]:
    """
    Get the chain of migrations between two revisions
    
    Args:
        start_revision: Starting revision (None for base)
        end_revision: Ending revision (None for head)
        
    Returns:
        List of migrations in order
    """
    migrations = get_all_migrations()
    revision_map = {m.revision: m for m in migrations}
    
    # Find end migration
    end_migration = None
    if end_revision:
        end_migration = get_migration_by_revision(end_revision)
    else:
        # Find the head
        heads = [m for m in migrations if m.is_head]
        if heads:
            end_migration = heads[0]
    
    if not end_migration:
        return []
    
    # Build chain backwards
    chain = []
    current = end_migration
    
    while current:
        if start_revision and current.revision == start_revision:
            chain.append(current)
            break
        
        chain.append(current)
        
        if current.is_base or (start_revision and current.revision == start_revision):
            break
        
        # Handle multiple dependencies (merge migrations)
        if current.is_merge:
            # For merge migrations, we need to choose a path
            # This is simplified - in practice you'd need to handle multiple paths
            if current.dependencies:
                current = current.dependencies[0]
            else:
                break
        else:
            if current.down_revision and current.down_revision in revision_map:
                current = revision_map[current.down_revision]
            else:
                break
    
    # Reverse to get chronological order
    return list(reversed(chain))


def format_migration_tree() -> str:
    """
    Format migrations as a tree structure for display
    
    Returns:
        ASCII tree representation
    """
    migrations = get_all_migrations()
    revision_map = {m.revision: m for m in migrations}
    
    # Find roots (bases)
    roots = [m for m in migrations if m.is_base]
    
    lines = []
    
    def build_tree(node, prefix="", is_last=True):
        if not node:
            return
        
        # Add current node
        marker = "└── " if is_last else "├── "
        lines.append(f"{prefix}{marker}{node.revision_short}: {node.description}")
        
        # Prepare for children
        new_prefix = prefix + ("    " if is_last else "│   ")
        
        # Find children (migrations that depend on this one)
        children = []
        for m in migrations:
            if m.down_revision:
                if isinstance(m.down_revision, list):
                    if node.revision in m.down_revision:
                        children.append(m)
                elif m.down_revision == node.revision:
                    children.append(m)
        
        # Sort children by creation date
        children.sort(key=lambda x: x.create_date)
        
        # Build tree for each child
        for i, child in enumerate(children):
            build_tree(child, new_prefix, i == len(children) - 1)
    
    # Build tree for each root
    for i, root in enumerate(roots):
        build_tree(root, "", i == len(roots) - 1)
    
    return "\n".join(lines)


# Initialize logging
logging.basicConfig(level=logging.INFO)

# Export commonly used functions
__all__.extend([
    'get_all_migrations',
    'format_migration_tree',
    'get_migration_chain',
    'MigrationInfo'
])


# Version package initialization
def init_package():
    """Initialize the versions package"""
    logger.info(f"Initializing migration versions package v{__version__}")
    
    # Validate migrations on import
    is_valid, issues = validate_migrations()
    if not is_valid:
        logger.warning("Migration validation found issues:")
        for issue in issues:
            logger.warning(f"  - {issue}")
    else:
        logger.info("Migration validation passed")
    
    # Log migration count
    migrations = get_all_migrations()
    logger.info(f"Found {len(migrations)} migration(s)")
    
    heads = [m for m in migrations if m.is_head]
    if heads:
        logger.info(f"Current head(s): {[h.revision_short for h in heads]}")


# Run initialization
init_package()


# For backwards compatibility
def __getattr__(name):
    """Handle deprecated attributes"""
    if name == 'get_version_info':
        logger.warning("get_version_info() is deprecated, use get_all_migrations() instead")
        return get_all_migrations
    raise AttributeError(f"module {__name__} has no attribute {name}")