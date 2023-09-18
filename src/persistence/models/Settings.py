from sqlalchemy.orm import Mapped, mapped_column
from .AbstractBase import AbstractBase


class Settings(AbstractBase):
    """
    Provides system settings
    """
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ac_management_enabled: Mapped[bool]

    def __init__(self, ac_management_enabled: bool):
        super().__init__(ac_management_enabled=ac_management_enabled)
