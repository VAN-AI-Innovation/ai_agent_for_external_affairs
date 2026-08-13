from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    task: str = Field(..., min_length=1, description="User request for the agent")
    context: str | None = Field(default=None, description="Optional business context")
    capability: str | None = Field(default=None, description="Optional capability key")


class AgentRunResponse(BaseModel):
    result: str
