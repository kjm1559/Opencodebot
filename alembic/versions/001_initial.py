"""001_initial

Revision ID: 001_initial
Revises:
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create all tables."""
    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_companies_ticker'), 'companies', ['ticker'], unique=True)
    
    # Create articles table
    op.create_table(
        'articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('url', sa.String(length=2000), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('provider_article_id', sa.String(length=200), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url'),
        sa.UniqueConstraint('content_hash'),
    )
    op.create_index(op.f('ix_articles_content_hash'), 'articles', ['content_hash'], unique=True)
    op.create_index(op.f('ix_articles_source'), 'articles', ['source'])
    op.create_index(op.f('ix_articles_published_at'), 'articles', ['published_at'])
    
    # Create article_companies association table
    op.create_table(
        'article_companies',
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('article_id', 'company_id'),
    )
    
    # Create article_signals table
    op.create_table(
        'article_signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('article_id'),
    )
    op.create_index(op.f('ix_article_signals_article_id'), 'article_signals', ['article_id'])


def downgrade():
    """Drop all tables."""
    op.drop_index(op.f('ix_article_signals_article_id'), table_name='article_signals')
    op.drop_table('article_signals')
    
    op.drop_table('article_companies')
    
    op.drop_index(op.f('ix_articles_source'), table_name='articles')
    op.drop_index(op.f('ix_articles_published_at'), table_name='articles')
    op.drop_index(op.f('ix_articles_content_hash'), table_name='articles')
    op.drop_table('articles')
    
    op.drop_index(op.f('ix_companies_ticker'), table_name='companies')
    op.drop_table('companies')
