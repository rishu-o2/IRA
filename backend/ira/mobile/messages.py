import json
from dataclasses import dataclass, asdict

@dataclass
class MessageBase:
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, data: str):
        return cls.from_dict(json.loads(data))

@dataclass
class CommandMessage(MessageBase):
    command: str
    session_id: str | None = None

@dataclass
class StatusMessage(MessageBase):
    running: bool
    assistant: str
    version: str
    device: str
    goals: int
    memory: bool

@dataclass
class ResponseMessage(MessageBase):
    handled: bool
    response: str
    execution_ms: int

@dataclass
class HeartbeatMessage(MessageBase):
    alive: bool
