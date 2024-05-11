"""initial structure

Revision ID: 19f4f2ae3f19
Revises: 
Create Date: 2024-05-11 11:41:13.866185

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "19f4f2ae3f19"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
            CREATE TABLE images (
                id SERIAL PRIMARY KEY,
                path VARCHAR NOT NULL,
                hash VARCHAR UNIQUE NOT NULL,
                original_name VARCHAR NOT NULL
            );
        """
    )
    op.execute(
        """
            CREATE TABLE searches (
                id SERIAL PRIMARY KEY,
                term VARCHAR NOT NULL,
                timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL
            );
        """
    )
    op.execute(
        """
            CREATE TABLE search_results (
                id SERIAL PRIMARY KEY,
                search_id INTEGER NOT NULL,
                image_id INTEGER NOT NULL,
                source_url VARCHAR NOT NULL,
                seen_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                FOREIGN KEY (search_id) REFERENCES searches(id),
                FOREIGN KEY (image_id) REFERENCES images(id)
            );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE search_results;")
    op.execute("DROP TABLE searches;")
    op.execute("DROP TABLE images;")
