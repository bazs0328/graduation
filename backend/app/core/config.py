import os
from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True)
class Settings:
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str
    database_url: str


def _build_database_url(
    mysql_host: str,
    mysql_port: int,
    mysql_user: str,
    mysql_password: str,
    mysql_database: str,
) -> str:
    password = quote_plus(mysql_password)
    return (
        "mysql+pymysql://"
        f"{mysql_user}:{password}@{mysql_host}:{mysql_port}/{mysql_database}" 
        "?charset=utf8mb4"
    )


def load_settings() -> Settings:
    mysql_host = os.getenv("MYSQL_HOST", "localhost")
    mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user = os.getenv("MYSQL_USER", "app_user")
    mysql_password = os.getenv("MYSQL_PASSWORD", "app_pass")
    mysql_database = os.getenv("MYSQL_DATABASE", "app_db")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = _build_database_url(
            mysql_host=mysql_host,
            mysql_port=mysql_port,
            mysql_user=mysql_user,
            mysql_password=mysql_password,
            mysql_database=mysql_database,
        )

    return Settings(
        mysql_host=mysql_host,
        mysql_port=mysql_port,
        mysql_user=mysql_user,
        mysql_password=mysql_password,
        mysql_database=mysql_database,
        database_url=database_url,
    )