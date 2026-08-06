"""The problem statement both deciders read, importable without a solver.

:class:`Shape`, the ending names and :func:`all_shapes` used to live in
:mod:`.abstract`, which imports ortools at module scope — so the solver-free
cross-check in :mod:`.independent` could not even be *imported* without the
``solver`` extra, and was untestable exactly when no solver was installed.
Nothing here needs one.

A shape is the block sequence of a game's `K` **segment endpoints** — its
critical moves plus, when quiet moves follow the last of them, the terminal
endpoint that closes the game. See the rubric in :mod:`.abstract` for why that
convention, and not critical-moves-alone, is the one the checkmate branch is
sound under.
"""

from __future__ import annotations

from dataclasses import dataclass

CHECKMATE = "checkmate"
DRAW = "draw"
ENDINGS = (CHECKMATE, DRAW)


def require_ending(ending: str) -> str:
    """Reject anything that is not a modelled ending, loudly.

    Silently reading an unknown string as a draw is the failure this exists to
    stop: the draw branch has the *higher* capture ceiling, so a typo would
    quietly relax the model and every verdict from it would be about a game
    nobody asked about.
    """
    if ending not in ENDINGS:
        raise ValueError(f"ending must be one of {ENDINGS}, got {ending!r}")
    return ending


@dataclass(frozen=True, slots=True)
class Shape:
    """A sequence of single-colour blocks, e.g. ``("B", "W", "B")``.

    The blocks are maximal runs of the game's `K` **segment endpoints**, not of
    its critical moves alone — see the rubric in :mod:`.abstract`. The
    distinction is what makes :attr:`mating_colour` sound.

    Maximality is validated, not assumed: :attr:`switches` reads `S` off the
    block count, which is only right when consecutive blocks differ in colour.
    A non-alternating tuple used to be accepted and silently miscounted.
    """

    colours: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.colours:
            raise ValueError("a shape needs at least one block")
        if any(colour not in ("B", "W") for colour in self.colours):
            raise ValueError(f"blocks are 'B' or 'W', got {self.colours!r}")
        for first, second in zip(self.colours, self.colours[1:], strict=False):
            if first == second:
                raise ValueError(
                    "blocks are maximal single-colour runs, so consecutive "
                    f"blocks must differ: {self.colours!r}"
                )

    @property
    def switches(self) -> int:
        """S, counting the virtual Black critical move before ply 1."""
        return len(self.colours) - 1 if self.colours[0] == "B" else len(self.colours)

    @property
    def mating_colour(self) -> str:
        """The side that gives mate, when the game ends in one.

        Correct because shapes are endpoint sequences and the mate is the
        game's last endpoint, so it sits in the last block by construction.
        Over critical-move sequences alone this would be false — a quiet mate
        can come from the other colour — and the checkmate branch built on it
        would be stronger than legality. See the rubric in :mod:`.abstract`.
        """
        return self.colours[-1]

    def blocks_of(self, colour: str) -> list[int]:
        return [i for i, c in enumerate(self.colours) if c == colour]

    def __str__(self) -> str:
        return " ".join(self.colours)


def all_shapes(max_blocks: int = 4) -> list[Shape]:
    """Every alternating block sequence up to ``max_blocks`` long."""
    shapes = []
    for length in range(1, max_blocks + 1):
        for first in ("B", "W"):
            colours = tuple(
                first if index % 2 == 0 else ("W" if first == "B" else "B")
                for index in range(length)
            )
            shapes.append(Shape(colours))
    return shapes
