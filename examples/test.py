from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar


T = TypeVar("T")
T_CO = TypeVar("T_CO", covariant=True)
V = TypeVar("V")
V_CO = TypeVar("V_CO", covariant=True)

class BaseReply(Protocol[T_CO]):
    pass

class ReplyProtocol(BaseReply[T], Protocol[V]):
    reply_to: V

class ReplyWrapper(ReplyProtocol[T, V]):
    reply_to: V

class Holder(Generic[T]):
    q: str

    def ask(self, msg: ReplyProtocol[T, V]) -> V:
        return msg.reply_to

@dataclass
class Question:
    reply_to: str

@dataclass
class InvalidQuestion:
    reply_to: str

h = Holder[Question]()

data = Question(reply_to="asd")
data2 = InvalidQuestion(reply_to="asd")

answer = h.ask(data)
answer2 = h.ask(data2)

