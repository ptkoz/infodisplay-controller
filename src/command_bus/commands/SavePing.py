import logging
from datetime import datetime
from AirConditionerService import AirConditionerService
from persistence import AirConditionerPingRepository, AirConditionerStatusLogRepository
from ui import AcPing
from .AbstractCommand import AbstractCommand
from .EvaluateAirConditioning import EvaluateAirConditioning
from ..ExecutionContext import ExecutionContext


class SavePing(AbstractCommand):
    """
    Command that saves received air conditioner ping in the persistence layer
    """

    def __init__(self, timestamp: datetime):
        self.timestamp = timestamp

    def execute(self, context: ExecutionContext) -> None:
        """
        Execute the command
        """
        logging.debug("Saving ping")

        ping_repository = AirConditionerPingRepository(context.db_session)
        air_conditioner = AirConditionerService(
            ping_repository,
            AirConditionerStatusLogRepository(context.db_session),
            context.time_source,
            context.radio,
            context.publisher
        )

        was_previously_online = air_conditioner.is_available()

        ping_repository.create(self.timestamp)
        context.publisher.publish(AcPing(self.timestamp))

        if not was_previously_online:
            # air conditioner came back online after period of inactivity, assume it was off and
            # evaluate whether we should turn it on
            air_conditioner.assume_off_status()
            context.command_queue.put_nowait(EvaluateAirConditioning())
