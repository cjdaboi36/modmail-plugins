from __future__ import annotations

import datetime
import json
import math
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

import discord
from discord.ext import commands

from core import checks
from core.models import PermissionLevel, getLogger

if TYPE_CHECKING:
    from bot import ModmailBot

info_json = Path(__file__).parent.resolve() / "info.json"
with open(info_json, encoding="utf-8") as f:
    __plugin_info__ = json.loads(f.read())

__plugin_name__ = __plugin_info__["name"]
__version__ = __plugin_info__["version"]

logger = getLogger(__name__)

API_BASE = "https://bots.wantuh.com"
MIGRATE_ENDPOINT = API_BASE + "/api/migrate/plugin"
CHUNK_SIZE = 2000 


def _make_serializable(obj: Any) -> Any:
    """
    Recursively convert BSON/pymongo types to plain JSON-serializable Python objects.
    Handles ObjectId, datetime, Decimal128, Int64, and bytes without importing bson directly.
    """
    type_name = type(obj).__name__
    if type_name in ("ObjectId", "Decimal128", "Int64", "Int32", "Timestamp"):
        return str(obj)
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(v) for v in obj]
    return obj


def _serialize(docs: list) -> list:
    """Convert a list of BSON documents to JSON-safe plain Python dicts."""
    return [_make_serializable(doc) for doc in docs]


class Migrate(commands.Cog, name=__plugin_name__):
    """Exports all MongoDB collections to the Wantuh Modmail dashboard."""

    def __init__(self, bot: ModmailBot):
        self.bot: ModmailBot = bot


    async def _update_embed(
        self,
        msg: discord.Message,
        title: str,
        color: int,
        collection_names: list,
        results: Dict[str, str],
        footer: Optional[str] = None,
    ) -> None:
        embed = discord.Embed(title=title, color=color)
        lines = [f"**{n}**: {results.get(n, 'Waiting')}" for n in collection_names]
        embed.description = "\n".join(lines)
        if footer:
            embed.set_footer(text=footer)
        await msg.edit(embed=embed)

    async def _post_chunk(
        self,
        token: str,
        collection: str,
        chunk_index: int,
        total_chunks: int,
        documents: list,
    ) -> dict:
        """POST a single chunk; raises on non-200."""
        payload = {
            "token": token,
            "collection": collection,
            "chunkIndex": chunk_index,
            "totalChunks": total_chunks,
            "documents": documents,
        }
        async with self.bot.api.session.post(
            MIGRATE_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
        ) as resp:
            body = await resp.json()
            if resp.status != 200:
                error = body.get("error", f"HTTP {resp.status}")
                raise RuntimeError(error)
            return body


    @commands.command(name="migrate")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def migrate(self, ctx: commands.Context, token: str):
        """
        Migrates all MongoDB collections to the Wantuh dashboard.

        Usage: `{prefix}migrate <token>`

        The migration token is generated on the Wantuh dashboard and is valid
        for 24 hours. The token is never stored — the invocation message is
        deleted immediately for security.

        Requires permission level: **Administrator (4)**.
        """
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        db = self.bot.api.db

        collection_names: list = await db.list_collection_names()
        if not collection_names:
            return await ctx.send(
                embed=discord.Embed(
                    title="Migration Error",
                    color=self.bot.error_color,
                    description="No collections found in the database.",
                )
            )

        collection_names.sort()

        results: Dict[str, str] = {}
        status_msg = await ctx.send(
            embed=discord.Embed(
                title="Migration Starting…",
                color=self.bot.main_color,
                description=(
                    f"Found **{len(collection_names)}** collection(s): "
                    + ", ".join(f"`{c}`" for c in collection_names)
                    + "\n\nPreparing…"
                ),
            )
        )

        overall_success = True
        masked_token = token[:32] + "…" if len(token) > 32 else token

        for coll_name in collection_names:
            results[coll_name] = "Fetching from DB…"
            await self._update_embed(
                status_msg,
                "Migration In Progress…",
                self.bot.main_color,
                collection_names,
                results,
                footer=f"Token: {masked_token}",
            )

            try:
                raw_docs = await db[coll_name].find({}).to_list(None)

                if not raw_docs:
                    results[coll_name] = "Empty — skipped"
                    continue

                docs = _serialize(raw_docs)
                total_docs = len(docs)
                total_chunks = math.ceil(total_docs / CHUNK_SIZE)
                total_inserted = 0

                logger.info(
                    "Migrating collection '%s': %d doc(s) in %d chunk(s).",
                    coll_name,
                    total_docs,
                    total_chunks,
                )

                for chunk_index in range(total_chunks):
                    chunk = docs[chunk_index * CHUNK_SIZE : (chunk_index + 1) * CHUNK_SIZE]

                    body = await self._post_chunk(
                        token=token,
                        collection=coll_name,
                        chunk_index=chunk_index,
                        total_chunks=total_chunks,
                        documents=chunk,
                    )

                    total_inserted = body.get("totalInserted", total_inserted)
                    results[coll_name] = (
                        f"Chunk {chunk_index + 1}/{total_chunks} — {total_inserted} docs sent"
                    )
                    await self._update_embed(
                        status_msg,
                        "Migration In Progress…",
                        self.bot.main_color,
                        collection_names,
                        results,
                        footer=f"Token: {masked_token}",
                    )

                    logger.debug(
                        "Collection '%s' chunk %d/%d — %d inserted so far.",
                        coll_name,
                        chunk_index + 1,
                        total_chunks,
                        total_inserted,
                    )

                results[coll_name] = f"Done — {total_inserted} docs"

            except RuntimeError as exc:
                logger.error("Collection '%s' migration failed: %s", coll_name, exc)
                results[coll_name] = f"API error: `{exc}`"
                overall_success = False

            except Exception as exc:
                logger.exception("Unexpected error migrating collection '%s'.", coll_name)
                results[coll_name] = f"`{type(exc).__name__}: {exc}`"
                overall_success = False

        await self._update_embed(
            status_msg,
            title="Migration Complete" if overall_success else "Migration Finished with Errors",
            color=self.bot.main_color if overall_success else self.bot.error_color,
            collection_names=collection_names,
            results=results,
            footer=f"Requested by {ctx.author}",
        )


async def setup(bot: ModmailBot) -> None:
    await bot.add_cog(Migrate(bot))
