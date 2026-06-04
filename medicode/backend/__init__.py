"""MediCode Python backend — FastAPI + SQLModel + Anthropic.

Replaces the original Jac backend. The REST surface intentionally mirrors
the Jac server (`/user/*`, `/walker/*` with a `{ok, data:{reports:[...]}}`
envelope and `_jac_id` node ids) so the existing React frontend works
unchanged.
"""
