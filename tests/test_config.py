import pytest

from pokerman.infrastructure.config import Settings


def make_settings(database_url: str = "postgresql+asyncpg://u:p@h:5432/db") -> Settings:
    return Settings(
        database_url=database_url,
        telegram_bot_token="token",
        telegram_bot_username="bot",
        telegram_webhook_secret="secret",
        public_base_url="https://example.onrender.com",
    )


class TestDatabaseUrlDriver:
    def test_rewrites_bare_postgresql_scheme_to_asyncpg(self) -> None:
        settings = make_settings("postgresql://user:pw@host:5432/db")

        assert settings.database_url == "postgresql+asyncpg://user:pw@host:5432/db"

    def test_rewrites_short_postgres_scheme_to_asyncpg(self) -> None:
        settings = make_settings("postgres://user:pw@host:5432/db")

        assert settings.database_url == "postgresql+asyncpg://user:pw@host:5432/db"

    def test_leaves_explicit_asyncpg_scheme_unchanged(self) -> None:
        settings = make_settings("postgresql+asyncpg://user:pw@host:5432/db")

        assert settings.database_url == "postgresql+asyncpg://user:pw@host:5432/db"

    def test_preserves_query_parameters(self) -> None:
        settings = make_settings("postgresql://user:pw@host:5432/db?sslmode=require")

        assert settings.database_url == "postgresql+asyncpg://user:pw@host:5432/db?sslmode=require"

    @pytest.mark.parametrize(
        "url",
        [
            "sqlite:///local.db",
            "postgresql+psycopg2://user:pw@host:5432/db",
        ],
    )
    def test_leaves_other_schemes_untouched(self, url: str) -> None:
        assert make_settings(url).database_url == url


class TestPublicBaseUrl:
    def test_strips_trailing_slash(self) -> None:
        settings = Settings(
            database_url="postgresql+asyncpg://u:p@h:5432/db",
            telegram_bot_token="token",
            telegram_bot_username="bot",
            telegram_webhook_secret="secret",
            public_base_url="https://example.onrender.com/",
        )

        assert settings.public_base_url == "https://example.onrender.com"

    def test_leaves_url_without_trailing_slash_unchanged(self) -> None:
        assert make_settings().public_base_url == "https://example.onrender.com"
