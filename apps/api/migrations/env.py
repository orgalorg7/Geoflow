from logging.config import fileConfig

from alembic import context
from geoflow_config import get_settings
from sqlalchemy import engine_from_config, pool, text

from geoflow_api.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.alembic_database_url)
target_metadata = Base.metadata


def include_name(
    name: str | None, object_type: str, parent_names: dict[str, str | None]
) -> bool:
    if object_type == "schema":
        return name in {None, "public"}
    if object_type == "table":
        schema_name = parent_names.get("schema_name")
        if schema_name not in {None, "public"}:
            return False
        return name not in {"alembic_version", "spatial_ref_sys"}
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # The PostGIS image adds topology and tiger to the database search path.
        # GeoFlow migrations own only public-schema application tables.
        connection.execute(text("SET search_path TO public"))
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
