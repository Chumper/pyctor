from logging import getLogger
from typing import Any, Optional

import pyctor.types
import pyctor.multiprocess.messages

logger = getLogger(__name__)

class LocalMessageStrategy(pyctor.types.MessageStrategy[pyctor.types.T]):
    """
    Should be used for local message sending
    """
    def transform_send_message(self, _: pyctor.types.Ref[pyctor.types.T], msg: pyctor.types.T) -> Any:
        """
        Do not transform the message for local refs
        """
        return msg

    def transform_stop_message(self, _: pyctor.types.Ref[pyctor.types.T]) -> Optional[Any]:
        """
        Locally we just want to stop the channel, 
        which is the default behavior if we return nothing
        """
        return None
    
class RemoteMessageStrategy(pyctor.types.MessageStrategy[pyctor.types.T]):
    """
    Should be used for remote message sending
    """
    def transform_send_message(self, me: pyctor.types.Ref[pyctor.types.T], msg: pyctor.types.T) -> Any:
        """
        Wrap the message in a wrapper message
        """
        return pyctor.multiprocess.messages.MessageCommand(ref=me, type=".".join([type(msg).__module__, type(msg).__name__]), msg=pyctor.configuration._default_encoder.encode(msg))


    def transform_stop_message(self, me: pyctor.types.Ref[pyctor.types.T]) -> Optional[Any]:
        """
        Send a StopCommand to the remote ref
        """
        return pyctor.multiprocess.messages.StopCommand(me)