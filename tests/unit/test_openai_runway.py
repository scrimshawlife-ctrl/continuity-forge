from typing import Any

from continuity_forge_compiler import compile_text
from continuity_forge_providers import OpenAIMediaWorker, RunwayMediaWorker, WorkerTask
from continuity_forge_shots import compile_shot_contracts

SOURCE = "INT. ROOM - DAY\n\nMara enters with a red keycard.\n\nMARA\nGo.\n"


def _contract() -> dict[str, Any]:
    document = compile_text(SOURCE, document_key="sdk-doc")
    return compile_shot_contracts(document).contracts[0].model_dump(mode="json")


class _FakeOpenAI:
    def generate_image(self, *, prompt: str, seed: str) -> dict[str, Any]:
        return {
            "provider": "openai",
            "model": "dall-e-3",
            "url": "https://example.test/img.png",
            "seed": seed,
            "prompt": prompt,
        }


class _FakeRunway:
    def create_generation(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        return {"id": "rw_1", "model": "gen3a_turbo", "status": "PENDING", "request": payload}


def test_openai_worker_with_injected_client() -> None:
    worker = OpenAIMediaWorker(client=_FakeOpenAI())
    candidate = worker.generate(shot_contract=_contract(), task=WorkerTask.IMAGE, seed="7")
    assert candidate.provider == "openai"
    assert candidate.authority.value == "PROPOSED"
    assert candidate.payload["remote"]["url"].startswith("https://")
    assert "Hard continuity" in candidate.feature_bag["prompt"] or candidate.feature_bag["prompt"]


def test_runway_worker_with_injected_transport() -> None:
    worker = RunwayMediaWorker(transport=_FakeRunway())
    candidate = worker.generate(shot_contract=_contract(), task=WorkerTask.VIDEO, seed="3")
    assert candidate.provider == "runway"
    assert candidate.authority.value == "PROPOSED"
    assert candidate.payload["remote"]["id"] == "rw_1"
