# docs/ — long-form audits behind the paper

The proof lives in [paper/main.tex](../paper/main.tex); the claims-to-code
map lives in [CLAIMS.md](../CLAIMS.md). These documents are the long-form
material behind the paper's Appendices A–B (computer verification), plus
the project's development history.

| document | role | backs |
|---|---|---|
| [optimality.md](optimality.md) | the whole argument in repository form, with the full correction records | paper §§2–5, App. B (audit record) |
| [abstract-model.md](abstract-model.md) | the CP-SAT/arithmetic cross-checks, constraint by constraint | paper App. B |
| [dead-positions.md](dead-positions.md) | why the witness needs no dead-position decision procedure; the one deadness fact the bound uses | paper App. A, B |
| [segment-independence.md](segment-independence.md) | why the rebuilt witness's segments cannot interfere | paper App. A |
| [movegen.md](movegen.md) | the independent C move generator: what it establishes, what it measurably does not, and the honest limits | paper App. A, B (future work) |

## Two implementation notes worth repeating

- **Checkmate outranks the 75-move draw.** The witness's final ply is
  simultaneously the 150th quiet ply of its segment and mate (FIDE 9.6.2's
  precedence clause). A verifier that tests the clock first scores it a
  draw — same length, wrong result.
- **Do not compare whole FENs for repetition.** The halfmove clock and move
  number play no part in position identity, and raw `ep_square` /
  `castling_rights` both over-distinguish. Use `has_legal_en_passant()` and
  `clean_castling_rights()` (FIDE 9.2.2).

Tom 7's `longest.cc` currently has `static constexpr int MOVE_RULE = 50;`
directly beneath a comment saying 75 is the correct value. That reference
implementation is not an oracle — which is the whole reason the verifier
here is independent.
