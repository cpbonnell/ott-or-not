import logging
import os
from logging.config import fileConfig

from alembic import context
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import URL
from sqlalchemy import create_engine

env_filename = find_dotenv()
print(f"Loading environment variables from: {env_filename}")
load_dotenv(env_filename)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# ========== BEGIN: Custom URL from environment ==========
# Check for the presence of all the necessary environment variables
# required to establish a database connection
logging.info(f"PGHOST: {os.getenv('PGHOST')}")
logging.info(f"PGPORT: {os.getenv('PGPORT')}")
logging.info(f"PGDATABASE: {os.getenv('PGDATABASE')}")
logging.info(f"PGUSER: {os.getenv('PGUSER')}")

pgpass_len = len(os.getenv("PGPASSWORD"))
if pgpass_len > 0:
    logging.info("Not echoing PGPASSWORD for security reasons.")
else:
    logging.warning(("PGPASSWORD is empty!"))

url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("PGUSER"),
    password=os.getenv("PGPASSWORD"),
    host=os.getenv("PGHOST"),
    port=os.getenv("PGPORT"),
    database=os.getenv("PGDATABASE"),
)
# ========== ========== ==========


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # connectable = engine_from_config(
    #     config.get_section(config.config_ini_section, {}),
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    # )

    connectable = create_engine(url)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
