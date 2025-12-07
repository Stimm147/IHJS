# src/ihjs/components/base.py
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class Component(BaseModel):
    tag: str = "div"
    children: List["Component"] = Field(default_factory=list)
    class_name: Optional[str] = Field(default=None, alias="class")

    model_config = ConfigDict(
        arbitrary_types_allowed=True, extra="allow", populate_by_name=True
    )

    def render(self) -> str:
        props_dict = self.model_dump(exclude={"children", "tag"}, by_alias=True)

        props = " ".join([f'{k}="{v}"' for k, v in props_dict.items() if v is not None])

        children_html = "".join([c.render() for c in self.children])

        return f"<{self.tag} {props}>{children_html}</{self.tag}>"
