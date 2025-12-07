from ihjs.components.base import Component


class Text(Component):
    tag: str = "span"
    content: str

    def __init__(self, content: str, **kwargs):
        super().__init__(content=content, **kwargs)

    def render(self) -> str:
        props = " ".join(
            [
                f'{k}="{v}"'
                for k, v in self.model_dump(
                    exclude={"children", "tag", "content"}
                ).items()
                if v is not None
            ]
        )
        return f"<{self.tag} {props}>{self.content}</{self.tag}>"


class Heading(Text):
    """Header h1-h6."""

    level: int = 1

    def __init__(self, content: str, level: int = 1, **kwargs):
        super().__init__(content=content, tag=f"h{level}", **kwargs)
