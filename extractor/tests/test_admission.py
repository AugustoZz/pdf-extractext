"""Tests del control de admisión (backpressure)."""
import asyncio

import pytest

from extractor_service.admission import Admission, Saturated


def test_admits_up_to_capacity_at_the_same_time():
    async def scenario():
        admission = Admission(capacity=2, wait_timeout=0.05)
        async with admission.slot(), admission.slot():
            return "ok"

    assert asyncio.run(scenario()) == "ok"


def test_rejects_when_no_slot_frees_up_in_time():
    async def scenario():
        admission = Admission(capacity=1, wait_timeout=0.05)
        async with admission.slot():
            async with admission.slot():
                pass

    with pytest.raises(Saturated):
        asyncio.run(scenario())


def test_waiting_request_gets_the_slot_when_it_is_released():
    async def scenario():
        admission = Admission(capacity=1, wait_timeout=1)
        order = []

        async def first():
            async with admission.slot():
                await asyncio.sleep(0.05)
                order.append("primera")

        async def second():
            await asyncio.sleep(0.01)
            async with admission.slot():
                order.append("segunda")

        await asyncio.gather(first(), second())
        return order

    assert asyncio.run(scenario()) == ["primera", "segunda"]


def test_releases_the_slot_when_processing_fails():
    async def scenario():
        admission = Admission(capacity=1, wait_timeout=0.05)
        with pytest.raises(RuntimeError):
            async with admission.slot():
                raise RuntimeError("falló la extracción")
        async with admission.slot():
            return "liberado"

    assert asyncio.run(scenario()) == "liberado"
