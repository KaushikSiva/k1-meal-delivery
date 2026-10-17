# Payload render assets

Reference research was performed with You.com on 2026-10-17; query receipts are
under `sim/research/you-{dominos-packaging,coke-can,coke-official}-20261017.json`.

- Domino’s reference: https://media.dominos.com/stories/recycling-pizza-boxes/
  The official corrugated-box photograph was inspected locally. It is not copied
  into these textures. The red/blue printed layout is an original approximation,
  not an exact current retail SKU. Closed box; pizza contents are not rendered.
- Coca-Cola reference: https://www.coca-cola.com/us/en/brands/coca-cola/products/original
  `coca-cola-wordmark.png` was retrieved from the official page's asset:
  https://www.coca-cola.com/content/dam/onexp/us/en/homepage/CocaColalogor.png
  The trademark image is used to depict the requested product; it is not CC0 or
  project-owned, and no endorsement is implied. The label wrap is a simulation
  approximation, not a retail label reproduction.
- `pizza-lid.png`, `pizza-side.png`, `coke-wrap.png` are built with
  `tools/build_payload_textures.py` (Pillow/NumPy; macOS Arial font).

The USD shells add cardboard folds, print, exposed corrugation, aluminum can rims,
lid and pull tab, and a pressed-steel tray with rubber liner. The existing assumed
payload dimensions, masses, collisions, torso bracket and four cup-holder walls
are unchanged. The new raised lip is **visual only**, with no collision retention.
The can is a sealed rigid proxy; no liquid simulation. These assets alter RGB
appearance and cannot establish camera-policy performance without new evaluation.
