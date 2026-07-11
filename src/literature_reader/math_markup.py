"""Local rendering for a small, useful subset of TeX-style math markup.

The annotation contract stays plain JSON, but model-written explanations can
mark mathematics with ``\\(...\\)`` for inline notation and ``\\[...\\]`` for a
displayed formula.  This module turns that explicit markup into browser-native
MathML for HTML and Office Math (OMML) for DOCX.  It deliberately has no CDN,
OCR, or network dependency.

It is not a general TeX engine.  It covers the notation normally needed when
explaining a paper: variables, Greek letters, grouped subscripts/superscripts,
fractions, common operators, and ``\\mathrm``/``\\text``/``\\mathcal`` labels.
Unknown commands are preserved as readable text rather than silently removed.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import re
from typing import Any, Literal


@dataclass(frozen=True)
class TextChunk:
    """Ordinary prose outside an explicit math delimiter."""

    text: str


@dataclass(frozen=True)
class MathChunk:
    """A TeX-style formula marked for inline or displayed rendering."""

    latex: str
    display: bool = False


MarkupChunk = TextChunk | MathChunk


@dataclass(frozen=True)
class _Sequence:
    children: tuple["_MathNode", ...]


@dataclass(frozen=True)
class _Symbol:
    value: str
    kind: Literal["identifier", "number", "operator", "text"] = "identifier"


@dataclass(frozen=True)
class _Script:
    base: "_MathNode"
    subscript: "_MathNode | None" = None
    superscript: "_MathNode | None" = None


@dataclass(frozen=True)
class _Fraction:
    numerator: "_MathNode"
    denominator: "_MathNode"


@dataclass(frozen=True)
class _Styled:
    content: "_MathNode"
    style: Literal["normal", "text", "script", "bold", "italic"]


_MathNode = _Sequence | _Symbol | _Script | _Fraction | _Styled


_MATH_DELIMITER = re.compile(
    r"(?s)(?P<display>\\\[(?P<display_body>.*?)\\\])|(?P<inline>\\\((?P<inline_body>.*?)\\\))|(?P<dollar>\$\$(?P<dollar_body>.*?)\$\$)"
)

_COMMAND_SYMBOLS = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "varepsilon": "ϵ",
    "zeta": "ζ",
    "eta": "η",
    "theta": "θ",
    "vartheta": "ϑ",
    "iota": "ι",
    "kappa": "κ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "xi": "ξ",
    "pi": "π",
    "rho": "ρ",
    "sigma": "σ",
    "tau": "τ",
    "upsilon": "υ",
    "phi": "φ",
    "varphi": "ϕ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
    "Gamma": "Γ",
    "Delta": "Δ",
    "Theta": "Θ",
    "Lambda": "Λ",
    "Xi": "Ξ",
    "Pi": "Π",
    "Sigma": "Σ",
    "Phi": "Φ",
    "Psi": "Ψ",
    "Omega": "Ω",
    "times": "×",
    "cdot": "·",
    "pm": "±",
    "mp": "∓",
    "le": "≤",
    "leq": "≤",
    "ge": "≥",
    "geq": "≥",
    "neq": "≠",
    "approx": "≈",
    "sim": "∼",
    "propto": "∝",
    "in": "∈",
    "notin": "∉",
    "subset": "⊂",
    "subseteq": "⊆",
    "cup": "∪",
    "cap": "∩",
    "to": "→",
    "rightarrow": "→",
    "leftarrow": "←",
    "leftrightarrow": "↔",
    "mapsto": "↦",
    "infty": "∞",
    "sum": "∑",
    "prod": "∏",
    "partial": "∂",
    "nabla": "∇",
    "ldots": "…",
    "dots": "…",
    "cdots": "⋯",
    "vert": "|",
    "mid": "|",
    "lvert": "|",
    "rvert": "|",
}

_STYLE_COMMANDS: dict[str, Literal["normal", "text", "script", "bold", "italic"]] = {
    "mathrm": "normal",
    "operatorname": "normal",
    "text": "text",
    "mathcal": "script",
    "mathbf": "bold",
    "mathit": "italic",
}

_SPACING_COMMANDS = {",", ";", ":", "!", "quad", "qquad", "enspace", " "}
_OPERATOR_CHARACTERS = set("+-=<>/|,;:()[]{}·×±∓≤≥≠≈∼∈∉→←↔↦∞∑∏∂∇")


def split_math_markup(text: str) -> tuple[MarkupChunk, ...]:
    """Split prose into escaped-safe text and explicitly delimited math chunks.

    A lone dollar sign is intentionally ordinary prose.  Requiring ``\\(...)``
    or ``\\[...]`` avoids accidentally treating prices, identifiers, or source
    text as a formula.
    """

    chunks: list[MarkupChunk] = []
    position = 0
    for match in _MATH_DELIMITER.finditer(text):
        if match.start() > position:
            chunks.append(TextChunk(text[position : match.start()]))
        if match.group("display") is not None:
            chunks.append(MathChunk(match.group("display_body") or "", display=True))
        elif match.group("dollar") is not None:
            chunks.append(MathChunk(match.group("dollar_body") or "", display=True))
        else:
            chunks.append(MathChunk(match.group("inline_body") or "", display=False))
        position = match.end()
    if position < len(text):
        chunks.append(TextChunk(text[position:]))
    return tuple(chunks) if chunks else (TextChunk(text),)


def render_html_markup(text: str) -> str:
    """Render marked formulae as self-contained, browser-native MathML."""

    rendered: list[str] = []
    for chunk in split_math_markup(text):
        if isinstance(chunk, TextChunk):
            rendered.append(escape(chunk.text))
            continue
        node = _parse_latex(chunk.latex)
        class_name = "math-display" if chunk.display else "math-inline"
        display_attr = ' display="block"' if chunk.display else ""
        label = escape(_plain_math(node), quote=True)
        rendered.append(
            f'<span class="{class_name}"><math xmlns="http://www.w3.org/1998/Math/MathML"'
            f'{display_attr} aria-label="{label}">{_mathml(node)}</math></span>'
        )
    return "".join(rendered)


def append_docx_markup(paragraph: Any, text: str) -> None:
    """Append prose and marked mathematics to a ``python-docx`` paragraph.

    ``python-docx`` does not expose Office Math in its public API, so the small
    OMML tree is added directly to the paragraph XML.  The resulting file keeps
    the formula editable in Word rather than flattening it into a picture.
    """

    for chunk in split_math_markup(text):
        if isinstance(chunk, TextChunk):
            if chunk.text:
                paragraph.add_run(chunk.text)
            continue
        if chunk.display:
            paragraph.add_run().add_break()
        paragraph._p.append(_omml(_parse_latex(chunk.latex)))
        if chunk.display:
            paragraph.add_run().add_break()


def _parse_latex(latex: str) -> _MathNode:
    return _LatexParser(latex).parse()


class _LatexParser:
    def __init__(self, source: str) -> None:
        self.source = source
        self.position = 0

    def parse(self, until: str | None = None) -> _MathNode:
        children: list[_MathNode] = []
        while self.position < len(self.source):
            character = self.source[self.position]
            if until and character == until:
                self.position += 1
                break
            if character.isspace():
                self.position += 1
                continue
            node = self._parse_atom()
            if node is None:
                continue
            while self.position < len(self.source) and self.source[self.position] in "^_":
                marker = self.source[self.position]
                self.position += 1
                argument = self._parse_group_or_atom()
                if isinstance(node, _Script):
                    node = _Script(
                        base=node.base,
                        subscript=argument if marker == "_" else node.subscript,
                        superscript=argument if marker == "^" else node.superscript,
                    )
                elif marker == "_":
                    node = _Script(base=node, subscript=argument)
                else:
                    node = _Script(base=node, superscript=argument)
            children.append(node)
        if not children:
            return _Sequence(())
        if len(children) == 1:
            return children[0]
        return _Sequence(tuple(children))

    def _parse_atom(self) -> _MathNode | None:
        character = self.source[self.position]
        if character == "{":
            self.position += 1
            return self.parse(until="}")
        if character == "\\":
            return self._parse_command()
        if character.isdigit():
            start = self.position
            while self.position < len(self.source) and (self.source[self.position].isdigit() or self.source[self.position] == "."):
                self.position += 1
            return _Symbol(self.source[start : self.position], "number")
        if character.isalpha():
            start = self.position
            while self.position < len(self.source) and self.source[self.position].isalpha():
                self.position += 1
            return _Symbol(self.source[start : self.position], "identifier")
        self.position += 1
        kind: Literal["identifier", "number", "operator", "text"] = (
            "operator" if character in _OPERATOR_CHARACTERS else "text"
        )
        return _Symbol(character, kind)

    def _parse_command(self) -> _MathNode | None:
        self.position += 1
        if self.position >= len(self.source):
            return _Symbol("\\", "text")
        if not self.source[self.position].isalpha():
            command = self.source[self.position]
            self.position += 1
            if command in _SPACING_COMMANDS:
                return None
            if command == "\\":
                return _Symbol(" ", "text")
            return _Symbol(command, "operator" if command in _OPERATOR_CHARACTERS else "text")

        start = self.position
        while self.position < len(self.source) and self.source[self.position].isalpha():
            self.position += 1
        command = self.source[start : self.position]
        if command in _SPACING_COMMANDS or command in {"displaystyle", "textstyle"}:
            return None
        if command in {"left", "right"}:
            return self._parse_atom()
        if command == "frac":
            numerator = self._parse_group_or_atom()
            denominator = self._parse_group_or_atom()
            return _Fraction(numerator, denominator)
        style = _STYLE_COMMANDS.get(command)
        if style:
            return _Styled(self._parse_group_or_atom(), style)
        symbol = _COMMAND_SYMBOLS.get(command)
        if symbol is not None:
            return _Symbol(symbol, "operator" if symbol in _OPERATOR_CHARACTERS else "identifier")
        return _Symbol(command, "text")

    def _parse_group_or_atom(self) -> _MathNode:
        while self.position < len(self.source) and self.source[self.position].isspace():
            self.position += 1
        if self.position >= len(self.source):
            return _Sequence(())
        return self._parse_atom() or _Sequence(())


def _mathml(node: _MathNode) -> str:
    if isinstance(node, _Sequence):
        return "<mrow>" + "".join(_mathml(child) for child in node.children) + "</mrow>"
    if isinstance(node, _Symbol):
        tag = "mi" if node.kind == "identifier" else "mn" if node.kind == "number" else "mo" if node.kind == "operator" else "mtext"
        return f"<{tag}>{escape(node.value)}</{tag}>"
    if isinstance(node, _Script):
        base = _mathml(node.base)
        if node.subscript is not None and node.superscript is not None:
            return f"<msubsup>{base}{_mathml(node.subscript)}{_mathml(node.superscript)}</msubsup>"
        if node.subscript is not None:
            return f"<msub>{base}{_mathml(node.subscript)}</msub>"
        return f"<msup>{base}{_mathml(node.superscript or _Sequence(()))}</msup>"
    if isinstance(node, _Fraction):
        return f"<mfrac>{_mathml(node.numerator)}{_mathml(node.denominator)}</mfrac>"
    if isinstance(node, _Styled):
        if node.style == "text":
            return f"<mtext>{escape(_plain_math(node.content))}</mtext>"
        variant = {"normal": "normal", "script": "script", "bold": "bold", "italic": "italic"}[node.style]
        return f'<mstyle mathvariant="{variant}">{_mathml(node.content)}</mstyle>'
    raise TypeError(f"Unsupported math node: {type(node)!r}")


def _plain_math(node: _MathNode) -> str:
    if isinstance(node, _Sequence):
        return "".join(_plain_math(child) for child in node.children)
    if isinstance(node, _Symbol):
        return node.value
    if isinstance(node, _Script):
        value = _plain_math(node.base)
        if node.subscript is not None:
            value += "_(" + _plain_math(node.subscript) + ")"
        if node.superscript is not None:
            value += "^(" + _plain_math(node.superscript) + ")"
        return value
    if isinstance(node, _Fraction):
        return f"({_plain_math(node.numerator)})/({_plain_math(node.denominator)})"
    if isinstance(node, _Styled):
        return _plain_math(node.content)
    raise TypeError(f"Unsupported math node: {type(node)!r}")


def _omml(node: _MathNode):
    from docx.oxml import OxmlElement

    math = OxmlElement("m:oMath")
    _append_omml_children(math, node)
    return math


def _append_omml_children(parent: Any, node: _MathNode, style: str | None = None) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    if isinstance(node, _Sequence):
        for child in node.children:
            _append_omml_children(parent, child, style)
        return
    if isinstance(node, _Symbol):
        run = OxmlElement("m:r")
        if style in {"normal", "text"}:
            run_properties = OxmlElement("m:rPr")
            math_style = OxmlElement("m:sty")
            math_style.set(qn("m:val"), "p")
            run_properties.append(math_style)
            run.append(run_properties)
        text = OxmlElement("m:t")
        text.text = node.value
        run.append(text)
        parent.append(run)
        return
    if isinstance(node, _Styled):
        _append_omml_children(parent, node.content, node.style)
        return
    if isinstance(node, _Fraction):
        fraction = OxmlElement("m:f")
        numerator = OxmlElement("m:num")
        denominator = OxmlElement("m:den")
        _append_omml_children(numerator, node.numerator, style)
        _append_omml_children(denominator, node.denominator, style)
        fraction.extend((numerator, denominator))
        parent.append(fraction)
        return
    if isinstance(node, _Script):
        if node.subscript is not None and node.superscript is not None:
            script = OxmlElement("m:sSubSup")
            subscript_tag = "m:sub"
            superscript_tag = "m:sup"
        elif node.subscript is not None:
            script = OxmlElement("m:sSub")
            subscript_tag = "m:sub"
            superscript_tag = None
        else:
            script = OxmlElement("m:sSup")
            subscript_tag = None
            superscript_tag = "m:sup"
        base = OxmlElement("m:e")
        _append_omml_children(base, node.base, style)
        script.append(base)
        if subscript_tag:
            subscript = OxmlElement(subscript_tag)
            _append_omml_children(subscript, node.subscript or _Sequence(()), style)
            script.append(subscript)
        if superscript_tag:
            superscript = OxmlElement(superscript_tag)
            _append_omml_children(superscript, node.superscript or _Sequence(()), style)
            script.append(superscript)
        parent.append(script)
        return
    raise TypeError(f"Unsupported math node: {type(node)!r}")
