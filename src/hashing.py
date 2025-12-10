
import hashlib

def compute_note_hash(title, contents, tags, embeddings, deleted):
    """
    Compute SHA-256 hex hash for a note's content state.
    embeddings: bytes (pickle dumped) or None
    deleted: int or bool
    """
    h = hashlib.sha256()
    # deterministic encoding order
    title_bytes = (title or "").encode("utf-8")
    contents_bytes = (contents or "").encode("utf-8")
    tags_bytes = (tags or "").encode("utf-8")

    h.update(b"title:")
    h.update(title_bytes)
    h.update(b"\ncontents:")
    h.update(contents_bytes)
    h.update(b"\ntags:")
    h.update(tags_bytes)
    h.update(b"\ndeleted:")
    h.update(str(int(bool(deleted))).encode("utf-8"))

    # embeddings could be bytes (pickle dumps) — include raw bytes
    if embeddings is not None:
        if isinstance(embeddings, memoryview):
            emb_bytes = bytes(embeddings)
        else:
            emb_bytes = embeddings
        # if embeddings is a string, encode it
        if isinstance(emb_bytes, str):
            emb_bytes = emb_bytes.encode("utf-8")
        h.update(b"\nembeddings:")
        h.update(emb_bytes)

    return h.hexdigest()

