"""Initialize original tables.

Revision ID: 609fbec99129
Revises: 
Create Date: 2024-06-11 20:17:05.800864

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "609fbec99129"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # Create the `image_metadata` table.
    op.execute(
        """
            CREATE TABLE IF NOT EXISTS image_metadata (
                hexdigest TEXT PRIMARY KEY,
                metadata JSON NOT NULL
            );
        """
    )


def downgrade() -> None:

    # Drop the `image_metadata` table.
    op.execute("DROP TABLE IF EXISTS image_metadata;")
