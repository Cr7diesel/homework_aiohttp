import json
from aiohttp import web
from sqlalchemy.exc import IntegrityError
from models import engine, Advertisement, Session, Base
from validation import validate, CheckCreateAdvert, CheckUpdateAdvert


app = web.Application()


async def orm_context(app: web.Application):
    print("start")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()
    print("stopped")


@web.middleware
async def session_middleware(requests: web.Request, handler):
    async with Session() as session:
        requests["session"] = session
        return await handler(requests)


app.cleanup_ctx.append(orm_context)
app.middlewares.append(session_middleware)


async def get_adverts(adverts_id: int, session: Session):
    adverts = await session.get(Advertisement, adverts_id)
    error = json.dumps({"status": "error", "message": "advertisement not found"})

    if adverts is None:
        raise web.HTTPNotFound(text=error, content_type="application/json")

    return adverts


class AdvertsView(web.View):
    async def get(self):
        session = self.request["session"]
        adverts_id = int(self.request.match_info["adverts_id"])
        adverts = await get_adverts(adverts_id, session)

        return web.json_response(
            {
                "id": adverts.id,
                "title": adverts.title,
                "description": adverts.description,
                "created_at": adverts.created_at.isoformat(),
                "owner": adverts.owner,
            }
        )

    async def post(self):
        session = self.request["session"]
        json_data = await self.request.json()
        data = validate(CheckCreateAdvert, json_data)
        adverts = Advertisement(**data)
        session.add(adverts)
        try:
            await session.commit()
        except IntegrityError:
            raise web.HTTPConflict(
                text=json.dumps(
                    {"status": "error", "message": "advertisement already exists"}
                ),
                content_type="application/json",
            )

        return web.json_response({"id": adverts.id})

    async def patch(self):
        adverts_id = int(self.request.match_info["adverts_id"])
        adverts = await get_adverts(adverts_id, self.request["session"])
        json_data = await self.request.json()
        data = validate(CheckUpdateAdvert, json_data)
        for field, value in data.items():
            setattr(adverts, field, value)
        self.request["session"].add(adverts)
        await self.request["session"].commit()
        return web.json_response({"status": "success"})

    async def delete(self):
        adverts_id = int(self.request.match_info["adverts_id"])
        adverts = await get_adverts(adverts_id, self.request["session"])
        await self.request["session"].delete(adverts)
        await self.request["session"].commit()
        return web.json_response({"status": "success"})


app.add_routes(
    [
        web.get("/adverts/{adverts_id:\d+}/", AdvertsView),
        web.post("/adverts/", AdvertsView),
        web.patch("/adverts/{adverts_id:\d+}/", AdvertsView),
        web.delete("/adverts/{adverts_id:\d+}/", AdvertsView),
    ]
)

if __name__ == "__main__":
    web.run_app(app)
