# Known limitations

- This is an experimental alpha; CLI and MCP schemas may change.
- `latest` is a moving upstream alias and does not guarantee reproducibility.
- No current GHG projections database was found in the verified Discodata metadata,
  so WEM/WAM and target-progress tools are not implemented.
- The upstream SQL allowlist is incompletely documented; valid T-SQL may be rejected.
- Deterministic pagination is conditional because tested `ORDER BY` queries sometimes
  returned upstream error `10002`.
- Policy effect estimates are sparse and null values never mean zero.
- Metadata does not declare database constraints; profile grains and joins must be
  rechecked when versions change.
- Query cancellation and a published service-level agreement are unavailable.

