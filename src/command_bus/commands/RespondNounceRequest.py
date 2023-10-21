import logging
from struct import pack
from secrets import MY_ADDRESS
from persistence import NounceRepository, NounceRequestResponseRepository
from radio_bus import OutboundMessage
from .AbstractCommand import AbstractCommand
from ..ExecutionContext import ExecutionContext


class RespondNounceRequest(AbstractCommand):
    """
    Class that informs devices about their nounce
    """

    def __init__(self, respond_to: int):
        self.respond_to = respond_to

    def execute(self, context: ExecutionContext) -> None:
        """
        Send nounce information to the device
        """
        nounce_repository = NounceRepository(context.db_session)
        outbound_nounce = nounce_repository.next_outbound_nounce(self.respond_to)
        last_inbound_nounce = nounce_repository.get_last_inbound_nounce(self.respond_to)

        logging.info(
            "Responding to nounce request from %#x with inbound: %d, outbound: %d",
            self.respond_to,
            last_inbound_nounce,
            outbound_nounce
        )

        context.outbound_bus.put_nowait(
            OutboundMessage(
                MY_ADDRESS,
                self.respond_to,
                0x00,
                outbound_nounce,
                pack("<L", last_inbound_nounce)
            )
        )

        nounce_request_response_repository = NounceRequestResponseRepository(context.db_session)
        nounce_request_response_repository.register(
            self.respond_to,
            context.time_source.now(),
            last_inbound_nounce,
            outbound_nounce
        )
