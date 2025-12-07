# src/ihjs/__init__.py
from ihjs.components.base import Component
from ihjs.components.typography import Text, Heading


def text(content: str, **kwargs) -> Text:
    return Text(content=content, **kwargs)


def heading(content: str, level: int = 1, **kwargs) -> Heading:
    return Heading(content=content, level=level, **kwargs)


def div(**kwargs) -> Component:
    return Component(tag="div", **kwargs)


__all__ = ["Component", "Text", "Heading", "text", "heading", "div"]
