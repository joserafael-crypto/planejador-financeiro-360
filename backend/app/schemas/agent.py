from pydantic import BaseModel, ConfigDict, Field


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=2, max_length=2000)


class DeterministicAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=2, max_length=2000)
    tool: str | None = None
    args: dict = Field(default_factory=dict)


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    agent_version: str
    question: str
    answer: str
    plan: list[dict]
    tools_used: list[str]
    provider: str
    model: str | None = None
    disclaimer: str
