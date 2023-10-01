from sqlalchemy.orm import Mapped, mapped_column

from .AbstractBase import AbstractBase


class Nounce(AbstractBase):
    """
    Representation of nounce numbers used by each device for both inbound and outbound communication.
    """

    __tablename__ = "nounce"
    owner: Mapped[int] = mapped_column(primary_key=True)
    inbound: Mapped[int]
    outbound: Mapped[int]
