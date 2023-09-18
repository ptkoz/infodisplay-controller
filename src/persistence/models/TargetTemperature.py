from sqlalchemy.orm import Mapped, mapped_column
from .AbstractBase import AbstractBase


class TargetTemperature(AbstractBase):
    """
    Represents configured target temperature
    """
    __acBoundary: float = 0.3
    __warningBoundary: float = 0.5

    __tablename__ = "target_temperature"
    id: Mapped[int] = mapped_column(primary_key=True)
    temperature_centi: Mapped[int]

    def __init__(self, temperature_id: int, temperature_centi: int):
        super().__init__(id=temperature_id, temperature_centi=temperature_centi)

    @property
    def temperature(self) -> float:
        """
        Returns float representation of the temperature
        :return:
        """
        return self.temperature_centi / 100

    def is_temperature_above_range(self, temperature: float) -> bool:
        """
        Checks if given temperature is higher than the threshold that enables AC
        """
        return temperature > self.temperature + self.__acBoundary

    def is_temperature_below_range(self, temperature: float) -> bool:
        """
        Checks if given temperature is lower than the threshold that disables AC
        """
        return temperature < self.temperature - self.__acBoundary

    def is_warning_temperature(self, temperature: float) -> bool:
        """
        Checks if given temperature is beyond a warning threshold (any direction)
        """
        return (
            temperature > self.temperature + self.__warningBoundary
            or temperature < self.temperature - self.__warningBoundary
        )
