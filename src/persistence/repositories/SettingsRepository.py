from persistence.models import Settings
from ._AbstractRepository import AbstractRepository


class SettingsRepository(AbstractRepository):
    """
    Repository for managing controller settings
    """

    def get_settings(self) -> Settings:
        """
        Returns the configured target temperature
        """
        s = self._session.query(Settings).first()

        if s is None:
            s = Settings(False)

            self._session.add(s)
            self._session.commit()

        return s
