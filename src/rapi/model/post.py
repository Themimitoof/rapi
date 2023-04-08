from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Post(BaseModel):
    id: str
    published_at: datetime
    modified_at: Optional[datetime] = Field(None)
    link: str
    title: str
    content: str
    featured_image: Optional[str] = Field(None)
    author: str
