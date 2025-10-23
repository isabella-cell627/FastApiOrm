"""
Full-Text Search Support for PostgreSQL

Provides utilities for PostgreSQL full-text search:
- Text search vector columns
- Search queries with ranking
- Language-specific search
- Phrase matching
- Search highlighting

Example:
    from fastapi_orm import create_search_vector, search_rank, search_query
    
    class Article(Model):
        __tablename__ = "articles"
        
        title: str = StringField(max_length=200)
        content: str = TextField()
        search_vector = create_search_vector('title', 'content')
    
    # Search articles
    results = await Article.search(
        session,
        "python fastapi",
        search_field="search_vector",
        rank_threshold=0.1
    )
"""

from typing import Any, List, Optional
from sqlalchemy import Column, Index, func, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.sql import expression


def create_search_vector(*column_names: str, language: str = 'english') -> Column:
    """
    Create a text search vector column.
    
    Args:
        *column_names: Names of text columns to index
        language: Text search language configuration (default: 'english')
    
    Returns:
        Column with TSVECTOR type
    
    Example:
        class Article(Model):
            __tablename__ = "articles"
            
            title: str = StringField(max_length=200)
            content: str = TextField()
            
            # Create search vector from title and content
            search_vector = create_search_vector('title', 'content')
            
            __table_args__ = (
                # Add GIN index for fast full-text search
                Index('idx_article_search', search_vector, postgresql_using='gin'),
            )
    """
    return Column(
        TSVECTOR,
        nullable=True
    )


def ts_query(query_text: str, language: str = 'english') -> expression:
    """
    Create a text search query expression.
    
    Args:
        query_text: Search query text
        language: Text search language configuration
    
    Returns:
        SQL expression for text search query
    
    Example:
        query = ts_query("python & (fastapi | django)")
        results = session.query(Article).filter(
            Article.search_vector.op('@@')(query)
        )
    """
    return func.to_tsquery(language, query_text)


def ts_rank(search_vector_column, query_text: str, language: str = 'english') -> expression:
    """
    Calculate relevance ranking for search results.
    
    Args:
        search_vector_column: The TSVECTOR column
        query_text: Search query text
        language: Text search language configuration
    
    Returns:
        SQL expression for ranking
    
    Example:
        rank = ts_rank(Article.search_vector, "python fastapi")
        results = session.query(Article, rank).filter(
            Article.search_vector.op('@@')(ts_query("python fastapi"))
        ).order_by(rank.desc())
    """
    query = ts_query(query_text, language)
    return func.ts_rank(search_vector_column, query)


def ts_headline(
    content_column,
    query_text: str,
    language: str = 'english',
    max_words: int = 35,
    min_words: int = 15,
    start_sel: str = '<b>',
    stop_sel: str = '</b>'
) -> expression:
    """
    Generate highlighted search snippets.
    
    Args:
        content_column: The text column to highlight
        query_text: Search query text
        language: Text search language configuration
        max_words: Maximum words in snippet
        min_words: Minimum words in snippet
        start_sel: HTML/markup to start highlighting
        stop_sel: HTML/markup to end highlighting
    
    Returns:
        SQL expression for highlighted text
    
    Example:
        headline = ts_headline(
            Article.content,
            "python fastapi",
            start_sel='<mark>',
            stop_sel='</mark>'
        )
        results = session.query(Article, headline).filter(
            Article.search_vector.op('@@')(ts_query("python fastapi"))
        )
    """
    query = ts_query(query_text, language)
    options = f'MaxWords={max_words}, MinWords={min_words}, StartSel={start_sel}, StopSel={stop_sel}'
    return func.ts_headline(language, content_column, query, options)


class SearchQuery:
    """
    Helper for building full-text search queries.
    """
    
    def __init__(self, query_text: str, language: str = 'english'):
        """
        Initialize a search query.
        
        Args:
            query_text: Search query text
            language: Text search language configuration
        """
        self.query_text = query_text
        self.language = language
    
    def and_query(self, other_text: str) -> "SearchQuery":
        """Combine queries with AND operator."""
        self.query_text = f"({self.query_text}) & ({other_text})"
        return self
    
    def or_query(self, other_text: str) -> "SearchQuery":
        """Combine queries with OR operator."""
        self.query_text = f"({self.query_text}) | ({other_text})"
        return self
    
    def not_query(self, other_text: str) -> "SearchQuery":
        """Exclude terms with NOT operator."""
        self.query_text = f"({self.query_text}) & !({other_text})"
        return self
    
    def phrase_query(self, phrase: str) -> "SearchQuery":
        """Search for exact phrase."""
        words = phrase.split()
        phrase_query = ' <-> '.join(words)
        self.query_text = phrase_query
        return self
    
    def to_tsquery(self) -> expression:
        """Convert to PostgreSQL tsquery expression."""
        return func.to_tsquery(self.language, self.query_text)


def create_search_trigger(
    table_name: str,
    search_vector_column: str,
    *text_columns: str,
    language: str = 'english'
) -> str:
    """
    Generate SQL for a trigger to auto-update search vectors.
    
    Args:
        table_name: Name of the table
        search_vector_column: Name of the search vector column
        *text_columns: Names of text columns to include
        language: Text search language configuration
    
    Returns:
        SQL string for creating the trigger
    
    Example:
        sql = create_search_trigger(
            'articles',
            'search_vector',
            'title',
            'content'
        )
        # Execute this SQL to create the trigger
        await session.execute(text(sql))
    """
    # Build the to_tsvector expression
    tsvector_parts = []
    weights = ['A', 'B', 'C', 'D']
    
    for idx, col in enumerate(text_columns):
        weight = weights[min(idx, len(weights) - 1)]
        tsvector_parts.append(f"setweight(to_tsvector('{language}', coalesce(NEW.{col}, '')), '{weight}')")
    
    tsvector_expr = ' || '.join(tsvector_parts)
    
    trigger_sql = f"""
CREATE OR REPLACE FUNCTION {table_name}_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.{search_vector_column} := {tsvector_expr};
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS {table_name}_search_vector_trigger ON {table_name};

CREATE TRIGGER {table_name}_search_vector_trigger
    BEFORE INSERT OR UPDATE ON {table_name}
    FOR EACH ROW EXECUTE FUNCTION {table_name}_search_vector_update();
"""
    
    return trigger_sql


# Mixin for models with full-text search
class FullTextSearchMixin:
    """
    Mixin that adds full-text search capabilities to a model.
    
    The model should have a search_vector column created with create_search_vector().
    
    Example:
        class Article(Model, FullTextSearchMixin):
            __tablename__ = "articles"
            
            title: str = StringField(max_length=200)
            content: str = TextField()
            search_vector = create_search_vector('title', 'content')
        
        # Search
        results = await Article.search(session, "python fastapi")
    """
    
    @classmethod
    async def search(
        cls,
        session,
        query_text: str,
        search_field: str = 'search_vector',
        language: str = 'english',
        rank_threshold: Optional[float] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by_rank: bool = True
    ) -> List[tuple]:
        """
        Perform full-text search on the model.
        
        Args:
            session: Database session
            query_text: Search query text
            search_field: Name of the search vector column
            language: Text search language
            rank_threshold: Minimum rank score (0.0-1.0)
            limit: Maximum number of results
            offset: Number of results to skip
            order_by_rank: Whether to order by relevance (default: True)
        
        Returns:
            List of tuples (instance, rank)
        
        Example:
            results = await Article.search(
                session,
                "python & fastapi",
                rank_threshold=0.1,
                limit=10
            )
            
            for article, rank in results:
                print(f"{article.title} (score: {rank})")
        """
        from sqlalchemy import select, func
        
        search_vector = getattr(cls, search_field)
        query = ts_query(query_text, language)
        rank = func.ts_rank(search_vector, query)
        
        stmt = select(cls, rank.label('rank')).where(
            search_vector.op('@@')(query)
        )
        
        if rank_threshold is not None:
            stmt = stmt.where(rank >= rank_threshold)
        
        if order_by_rank:
            stmt = stmt.order_by(rank.desc())
        
        stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        
        result = await session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
    
    @classmethod
    async def search_count(
        cls,
        session,
        query_text: str,
        search_field: str = 'search_vector',
        language: str = 'english'
    ) -> int:
        """
        Count search results.
        
        Args:
            session: Database session
            query_text: Search query text
            search_field: Name of the search vector column
            language: Text search language
        
        Returns:
            Number of matching records
        """
        from sqlalchemy import select, func
        
        search_vector = getattr(cls, search_field)
        query = ts_query(query_text, language)
        
        stmt = select(func.count()).select_from(cls).where(
            search_vector.op('@@')(query)
        )
        
        result = await session.execute(stmt)
        return result.scalar_one()
