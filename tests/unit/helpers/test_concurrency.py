import asyncio

import pytest

from app.helpers.concurrency import MAX_CONCURRENT_IMAGE_REQUESTS, get_image_semaphore


class TestConcurrency:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Semaphore should limit concurrent access."""
        sem = get_image_semaphore()
        active = 0
        max_active = 0

        async def worker():
            nonlocal active, max_active
            async with sem:
                active += 1
                max_active = max(max_active, active)
                await asyncio.sleep(0.01)
                active -= 1

        tasks = [worker() for _ in range(MAX_CONCURRENT_IMAGE_REQUESTS + 5)]
        await asyncio.gather(*tasks)

        assert max_active <= MAX_CONCURRENT_IMAGE_REQUESTS
        assert active == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_semaphore_singleton(self):
        """get_image_semaphore should return the same instance."""
        sem1 = get_image_semaphore()
        sem2 = get_image_semaphore()
        assert sem1 is sem2

    @pytest.mark.unit
    def test_default_limit(self):
        """Default limit should be 15."""
        assert MAX_CONCURRENT_IMAGE_REQUESTS == 15
