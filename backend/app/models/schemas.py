from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

# Feeds
class FeedBase(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    category: Optional[str] = None

class FeedCreate(FeedBase):
    pass

class Feed(FeedBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Articles
class ArticleBase(BaseModel):
    feed_id: int
    title: str
    content: Optional[str] = None
    url: HttpUrl
    published_date: Optional[datetime] = None

class Article(ArticleBase):
    id: int

    class Config:
        from_attributes = True

# Embeddings/Clusters
class ClusterBase(BaseModel):
    theme: str
    summary: str
    article_ids: List[int]
