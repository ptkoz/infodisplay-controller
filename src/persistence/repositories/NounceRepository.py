from persistence.models.Nounce import Nounce
from ._AbstractRepository import AbstractRepository


class NounceRepository(AbstractRepository):
    """
    Repository for air conditioner pings
    """

    def get_nounce(self, owner: int) -> Nounce:
        """
        Returns current nounce for given device
        """
        nounce = self._session.query(Nounce).filter(Nounce.owner == owner).first()
        if nounce is None:
            nounce = Nounce(owner=owner, inbound=0, outbound=0)
            self._session.add(nounce)

        return nounce

    def get_last_inbound_nounce(self, owner: int):
        """
        Returns most recently recorded inbound nounce
        """
        return self.get_nounce(owner).inbound

    def register_inbound_nounce(self, owner: int, value: int):
        """
        Returns most recently recorded nounce for given device kind
        """
        nounce = self.get_nounce(owner)
        nounce.inbound = value

    def next_outbound_nounce(self, owner: int) -> int:
        """
        Returns next nounce for outbound communication for given device
        """
        nounce = self.get_nounce(owner)
        nounce.outbound += 1

        return nounce.outbound
