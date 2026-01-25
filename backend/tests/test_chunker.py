from app.services.document_parser import build_chunks


def test_chunker_short_text():
    text = "hello world"
    chunks = build_chunks(text, chunk_size=8, overlap=2)
    assert len(chunks) == 2
    assert chunks[0]["text"] == "hello wo"
    assert chunks[1]["text"] == "world"
    assert chunks[0]["end"] - chunks[0]["start"] == 8
    assert chunks[1]["start"] == 6


def test_chunker_long_text_with_overlap():
    text = "a" * 20
    chunks = build_chunks(text, chunk_size=8, overlap=2)
    assert len(chunks) == 4
    assert chunks[0]["text"] == "a" * 8
    assert chunks[1]["text"] == "a" * 8
    assert chunks[2]["text"] == "a" * 8
    assert chunks[3]["text"] == "a" * 2
    assert chunks[0]["start"] == 0
    assert chunks[1]["start"] == 6
    assert chunks[2]["start"] == 12
    assert chunks[3]["start"] == 18
