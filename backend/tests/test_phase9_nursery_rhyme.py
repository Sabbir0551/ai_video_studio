import os
import pytest
from pathlib import Path
from backend.app.providers.llm.nursery_rhyme_engine import NurseryRhymeEngine
from backend.app.providers.llm.smart_script_engine import SmartScriptEngine
from backend.app.providers.image.generative_image_provider import GenerativeImageProvider


def test_nursery_rhyme_detection():
    assert NurseryRhymeEngine.is_nursery_rhyme("Rain Rain Go Away (Animal Version) _ Lalafun Nursery Rhymes & Kids Songs") is True
    assert NurseryRhymeEngine.is_nursery_rhyme("বৃষ্টি বৃষ্টি চলে যাও ছড়া গান") is True
    assert NurseryRhymeEngine.is_nursery_rhyme("CoComelon kids song for toddlers") is True
    assert NurseryRhymeEngine.is_nursery_rhyme("Quantum Computing Enterprise Cloud Architecture") is False


def test_smart_script_engine_nursery_generation():
    import asyncio
    engine = SmartScriptEngine()
    result = asyncio.run(engine.generate_script(
        topic_or_content="Rain Rain Go Away (Animal Version) _ Lalafun Nursery Rhymes & Kids Songs",
        language="en",
        target_duration=60.0
    ))

    assert len(result.scenes) >= 4
    assert "Rain" in result.scenes[0].narration or "rain" in result.scenes[0].narration.lower()
    
    # Check that individual scenes feature puppy, kitty, duckling, lamb
    first_four = " ".join(s.visual_intent.lower() for s in result.scenes[:4])
    assert "puppy" in first_four
    assert "kitten" in first_four or "kitty" in first_four or "cat" in first_four


def test_generative_image_provider_multi_animal_fallbacks(tmp_path):
    provider = GenerativeImageProvider()
    
    animals = ["puppy", "kitten", "duckling", "lamb", "rainbow"]
    generated_paths = []
    
    for idx, animal in enumerate(animals):
        out_p = str(tmp_path / f"animal_{animal}_{idx}.jpg")
        provider._render_rich_illustrated_fallback(
            prompt=f"3D Pixar CGI animation style, cute {animal} playing in rain",
            output_path=out_p,
            width=640,
            height=360,
            seed=1000 + idx * 500
        )
        assert os.path.exists(out_p)
        assert os.path.getsize(out_p) > 5000
        generated_paths.append(out_p)
    
    # Verify that different animal illustrations have different file contents
    hashes = set()
    for p in generated_paths:
        with open(p, "rb") as f:
            hashes.add(hash(f.read()))
    
    assert len(hashes) == len(animals)  # All 5 animal scenes must be visually unique!
