from context.chunker import CodeChunk, chunk_file


def test_python_function_split():
    source = """
def foo():
    return 1

def bar():
    return 2
"""
    chunks = chunk_file(source, language="python", filepath="mod.py")
    assert len(chunks) >= 2
    assert all(isinstance(c, CodeChunk) for c in chunks)
    assert all(c.filepath == "mod.py" for c in chunks)
    assert all(c.start_line >= 1 for c in chunks)
    assert all(len(c.content) > 0 for c in chunks)


def test_unsupported_language_falls_back():
    source = "line one\nline two\nline three\n" * 20
    chunks = chunk_file(source, language="elixir", filepath="app.ex")
    assert len(chunks) >= 1
    assert all(isinstance(c, CodeChunk) for c in chunks)


def test_empty_file_returns_empty():
    chunks = chunk_file("", language="python", filepath="empty.py")
    assert chunks == []


def test_chunk_has_token_count():
    source = "def hello():\n    pass\n"
    chunks = chunk_file(source, language="python", filepath="a.py")
    assert all(c.token_count > 0 for c in chunks)


def test_large_function_is_windowed():
    # A single function larger than 1000 tokens gets split into windows
    body = "    x = 1\n" * 250
    source = f"def big():\n{body}"
    chunks = chunk_file(source, language="python", filepath="big.py")
    assert len(chunks) >= 2
    assert all(c.token_count <= 1000 for c in chunks)


def test_chunk_has_function_name():
    source = "def authenticate(user, password):\n    return True\n"
    chunks = chunk_file(source, language="python", filepath="auth.py")
    assert len(chunks) == 1
    assert chunks[0].function_name == "authenticate"
    assert chunks[0].class_name is None


def test_chunk_has_class_name():
    source = "class UserService:\n    def get(self):\n        pass\n"
    chunks = chunk_file(source, language="python", filepath="service.py")
    assert len(chunks) >= 1
    assert any(c.class_name == "UserService" for c in chunks)
