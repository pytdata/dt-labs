from fastapi import APIRouter, Depends
from strawberry.fastapi import GraphQLRouter
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.graphql.schema import schema

async def get_context(db: AsyncSession = Depends(get_db)):
    return {"db": db}

graphql_app = GraphQLRouter(schema, context_getter=get_context)
router = APIRouter()
router.include_router(graphql_app, prefix="/graphql")
