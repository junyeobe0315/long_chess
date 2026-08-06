"""Regenerate the board diagrams in paper/figures/.

    uv run --with cairosvg python paper/figures/make_figures.py

Each diagram is produced by replaying the exact move sequence quoted in the
paper, so the figures cannot drift from the text. Output is vector PDF via
python-chess's SVG renderer.
"""

from __future__ import annotations

from pathlib import Path

import cairosvg
import chess
import chess.svg

HERE = Path(__file__).parent
SIZE = 320

# Lemma on the unresolved origin pair: the ten-move game.
CAP10 = (
    "Nf3 a6 Ng1 a5 Nf3 a4 Ng1 a3 Nxa3 Nc6 Nc4 Rb8 "
    "a3 Nf6 a4 Ng8 a5 Nf6 a6 Ng8 a7 Nf6 a8=Q Ng8"
)

# The home-rank lemma, minimal illustration: four single steps and stuck.
HOMERANK = "Nf3 e6 Ng1 e5 Nf3 e4 Ng1 e3"

# Appendix B, first instance: the legal game refuting the cap of 4.
CAP4_FALSE = "e4 a5 e5 a4 Bb5 Nc6 Bxa4 Rb8 Bb3 Nh6 a3 Ng4 a4 Nh6 a5"

# Appendix B, third instance: quiet mate by the colour that made no
# critical move last (critical actors B then W; Black mates).
QUIET_MATE = (
    "Nf3 Nf6 Ng1 Ng4 Nf3 Nxf2 Ng1 Nxh1 Nf3 Ng3 Ng1 Nxf1 Nf3 Nxd2 Ng1 Nb3 "
    "Nf3 Nxa1 Ng1 Nc6 Nf3 Nd4 Ng1 Nxe2 Nf3 Nxc1 Ng1 Nxa2 Nf3 Nb4 Ng1 Nd5 "
    "Nf3 Nc3 Ng1 Nxd1 Nf3 Nxb2 Ng1 d5 Nf3 Bf5 Ng1 Bxc2 Nf3 e6 Ng1 Bd6 "
    "Nf3 Bxh2 Ng1 h5 Nf3 h4 Ng1 h3 Nf3 hxg2 Ng1 Bxg1 "
    "Na3 Rh5 Nb1 Bc5 Na3 Bd6 Nb1 Bxb1 "
    "Kd2 Bd3 Ke3 Qh4 Kf3 Rf5+ Kxg2 Qh2#"
)

# The witness's final position, as verified: mate with the clock at 150.
WITNESS_FINAL = "3k4/3Q4/4K3/8/8/8/8/8 b - - 150 8849"


def play(san: str, upto: int | None = None) -> tuple[chess.Board, chess.Move]:
    board = chess.Board()
    last = None
    tokens = san.split()
    for token in tokens if upto is None else tokens[:upto]:
        last = board.parse_san(token)
        board.push(last)
    assert last is not None
    return board, last


def write(name: str, board: chess.Board, lastmove: chess.Move | None) -> None:
    svg = chess.svg.board(
        board, size=SIZE, coordinates=True, lastmove=lastmove, borders=False
    )
    out = HERE / f"{name}.pdf"
    cairosvg.svg2pdf(bytestring=svg.encode(), write_to=str(out))
    # cairo stamps PDF 1.7 while using nothing beyond 1.5 for these plain
    # vector drawings; down-stamp so including them in a 1.5 document does
    # not warn on every build.
    data = out.read_bytes()
    if data.startswith(b"%PDF-1.7"):
        out.write_bytes(b"%PDF-1.5" + data[8:])
    print(f"{out.name}: {board.fen()}")


def main() -> None:
    # (a) after 4...a3: Black's pawn has made four moves and is about to be
    # captured by the b1 knight; (b) the final position, ten pawn moves made
    # and the a-file unresolved throughout.
    board, last = play(CAP10, upto=8)
    write("cap10-after", board, last)
    board, last = play(CAP10)
    write("cap10-final", board, last)

    board, last = play(HOMERANK)
    write("homerank", board, last)

    board, last = play(CAP4_FALSE)
    write("cap4-false", board, last)

    board, last = play(QUIET_MATE)
    assert board.is_checkmate()
    write("quiet-mate", board, last)

    board = chess.Board(WITNESS_FINAL)
    assert board.is_checkmate()
    write("witness-final", board, None)


if __name__ == "__main__":
    main()
