from typing import Any


def clean_document(document: dict[str, Any]) -> dict[str, Any]:
    document = {k: v for k, v in document.items() if not k.startswith("_")}
    return document
