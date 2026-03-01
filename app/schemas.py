from dataclasses import dataclass

from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    github_url: str = Field(..., description="URL of a public GitHub repository")


class SummarizeResponse(BaseModel):
    summary: str
    technologies: list[str]
    structure: str


@dataclass
class RepoRef:
    owner: str
    repo: str
