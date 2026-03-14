import math
from dataclasses import dataclass, field
from typing import List
from enum import Enum


CLOSE_THRESHOLD = 15


@dataclass
class IconPalette:
    name: str
    background: str
    icon: str
    accent: str


ICON_PALETTES: List[IconPalette] = [
    IconPalette("Ink",       "#f8f8f8", "#1a1a1a", "#e63946"),
    IconPalette("Blueprint", "#dceefb", "#1d3557", "#457b9d"),
    IconPalette("Forest",    "#edf7ee", "#1b4332", "#52b788"),
    IconPalette("Ember",     "#fff3e0", "#7f2e00", "#ff6d00"),
    IconPalette("Lavender",  "#f3e8ff", "#4a148c", "#9c27b0"),
    IconPalette("Slate",     "#eceff1", "#263238", "#00bcd4"),
    IconPalette("Rose",      "#fce4ec", "#880e4f", "#e91e63"),
    IconPalette("Sage",      "#f1f8e9", "#2e4a1e", "#7cb342"),
    IconPalette("Midnight",  "#0d1117", "#e6edf3", "#58a6ff"),
    IconPalette("Sand",      "#fdf6e3", "#4a3728", "#d4a853"),
]


class ShapeType(Enum):
    LINE = "line"
    CIRCLE = "circle"
    SQUARE = "square"
    TRIANGLE = "triangle"
    PATH = "path"
    TEXT = "text"


class ToolMode(Enum):
    SELECT = "select"
    DRAW = "draw"


@dataclass
class Shape:
    shape_type: ShapeType
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    rotation: float = 0.0
    stroke_width: float = 10.0
    stroke_color: str = "#000000"
    corner_radius: float = 0.0
    points: List = field(default_factory=list)
    curves: List = field(default_factory=list)
    closed: bool = False
    text: str = ""
    font_family: str = "Arial Rounded MT Bold"
    font_size: int = 24
    id: str = field(default_factory=lambda: str(hash(id(__import__('time').time()))))

    def to_dict(self):
        return {
            "type": self.shape_type.value,
            "start_x": self.start_x,
            "start_y": self.start_y,
            "end_x": self.end_x,
            "end_y": self.end_y,
            "rotation": self.rotation,
            "stroke_width": self.stroke_width,
            "stroke_color": self.stroke_color,
            "corner_radius": self.corner_radius,
            "points": self.points,
            "curves": self.curves,
            "closed": self.closed,
            "text": self.text,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "id": self.id,
        }

    @staticmethod
    def from_dict(data):
        return Shape(
            shape_type=ShapeType(data["type"]),
            start_x=data["start_x"],
            start_y=data["start_y"],
            end_x=data["end_x"],
            end_y=data["end_y"],
            rotation=data.get("rotation", 0.0),
            stroke_width=data.get("stroke_width", 10.0),
            stroke_color=data.get("stroke_color", "#000000"),
            corner_radius=data.get("corner_radius", 0.0),
            points=data.get("points", []),
            curves=data.get("curves", []),
            closed=data.get("closed", False),
            text=data.get("text", ""),
            font_family=data.get("font_family", "Arial Rounded MT Bold"),
            font_size=data.get("font_size", 24),
            id=data.get("id", str(hash(id(__import__('time').time())))),
        )
