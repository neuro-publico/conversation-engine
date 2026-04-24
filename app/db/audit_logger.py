import json
import os
import uuid

_pool = None


async def init_pool():
    """Initialize asyncpg connection pool. Fails silently if not configured."""
    global _pool
    host = os.getenv("AUDIT_DB_HOST", "")
    if not host:
        print("[AUDIT] AUDIT_DB_HOST not set — prompt logging disabled", flush=True)
        return
    try:
        import asyncpg

        _pool = await asyncpg.create_pool(
            host=host,
            port=int(os.getenv("AUDIT_DB_PORT", "5432")),
            user=os.getenv("AUDIT_DB_USER", ""),
            password=os.getenv("AUDIT_DB_PASSWORD", ""),
            database=os.getenv("AUDIT_DB_NAME", "analytics"),
            min_size=2,
            max_size=10,
            command_timeout=10,
        )
        print(f"[AUDIT] Connected to {host}/{os.getenv('AUDIT_DB_NAME', 'analytics')}", flush=True)
    except Exception as e:
        print(f"[AUDIT] Failed to connect to audit DB: {e}", flush=True)
        _pool = None


async def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def log_prompt(
    log_type: str,
    prompt: str = None,
    response_text: str = None,
    response_url: str = None,
    owner_id: str = None,
    website_id: str = None,
    agent_id: str = None,
    model: str = None,
    provider: str = None,
    brand_colors: list = None,
    status: str = "success",
    error_message: str = None,
    attempt_number: int = None,
    fallback_used: bool = False,
    elapsed_ms: int = None,
    metadata: dict = None,
):
    """Fire-and-forget prompt audit log. Never raises, never blocks."""
    if not _pool:
        return
    try:
        async with _pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO prompt_logs (
                    id, log_type, owner_id, website_id, agent_id,
                    model, provider, prompt, response_text, response_url,
                    brand_colors, status, error_message, attempt_number,
                    fallback_used, elapsed_ms, metadata
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17
                )
                """,
                str(uuid.uuid4()),
                log_type,
                owner_id,
                website_id,
                agent_id,
                model,
                provider,
                prompt,
                response_text[:100000] if response_text else None,
                response_url,
                json.dumps(brand_colors) if brand_colors else None,
                status,
                error_message[:1000] if error_message else None,
                attempt_number,
                fallback_used,
                elapsed_ms,
                json.dumps(metadata) if metadata else None,
            )
    except Exception as e:
        print(f"[AUDIT-ERROR] {e}", flush=True)
