from persistence.models.Nounce import Nounce
from ._AbstractRepository import AbstractRepository


class NounceRepository(AbstractRepository):
    """
    Repository for air conditioner pings
    """

    def get_current_nounce(self, owner: int) -> Nounce:
        """
        Returns current nounce for given device
        """
        nounce = self._session.query(Nounce).filter(Nounce.owner == owner).first()
        if nounce is None:
            nounce = Nounce(owner=int, inboud=0, outbound=0)

        return nounce

    def register_inbound_nounce(self, owner: int, value: int):
        """
        Returns most recently recorded ping for given device kind
        """
        nounce = self.get_current_nounce(owner)
        nounce.inbound = value

        self._session.commit()

    def next_outbound_nounce(self, owner: int) -> int:
        """
        Creates and records new ping object with given timestamp and device kind
        """
        nounce = self.get_current_nounce(owner)
        nounce.outbound += 1
        self._session.commit()

        return nounce.outbound