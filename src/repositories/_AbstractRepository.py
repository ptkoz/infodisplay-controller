from sqlalchemy.orm import Session


class AbstractRepository:
    """
    Base class for all repositories
    """
    def __init__(self, session: Session):
        self._session = session
