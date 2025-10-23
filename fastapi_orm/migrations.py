import os
from pathlib import Path
from alembic.config import Config
from alembic import command
from typing import Optional


class MigrationManager:
    def __init__(self, database_url: str, migrations_dir: str = "migrations"):
        self.database_url = database_url
        self.migrations_dir = Path(migrations_dir)
        self.alembic_ini = self.migrations_dir / "alembic.ini"

    def init(self):
        if not self.migrations_dir.exists():
            alembic_cfg = Config()
            alembic_cfg.set_main_option("script_location", str(self.migrations_dir))
            alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
            
            command.init(alembic_cfg, str(self.migrations_dir))
            
            env_py_path = self.migrations_dir / "env.py"
            if env_py_path.exists():
                content = env_py_path.read_text()
                content = content.replace(
                    "target_metadata = None",
                    "from fastapi_orm.database import Base\ntarget_metadata = Base.metadata"
                )
                env_py_path.write_text(content)

    def create_migration(self, message: str):
        alembic_cfg = Config(str(self.alembic_ini))
        alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
        command.revision(alembic_cfg, message=message, autogenerate=True)

    def upgrade(self, revision: str = "head"):
        alembic_cfg = Config(str(self.alembic_ini))
        alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
        command.upgrade(alembic_cfg, revision)

    def downgrade(self, revision: str = "-1"):
        alembic_cfg = Config(str(self.alembic_ini))
        alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
        command.downgrade(alembic_cfg, revision)

    def current(self):
        alembic_cfg = Config(str(self.alembic_ini))
        alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
        command.current(alembic_cfg)

    def history(self):
        alembic_cfg = Config(str(self.alembic_ini))
        alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
        command.history(alembic_cfg)
