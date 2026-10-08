"""ProofPilot backend package root.

Layout note: `core` must stay importable without FastAPI or Pydantic installed, so this
package deliberately imports nothing at module level (see docs/HLD.md section 4).
"""
