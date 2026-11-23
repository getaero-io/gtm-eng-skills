# Three views of the same process

Open [the comparison](diagram-options.html).

| Format | Best use | Delivered |
|---|---|---|
| D2 | A short overview kept with the code | D2 source, SVG and PNG; used in the README |
| Excalidraw | Editing the flow in a discussion | Valid scene JSON and a labeled geometric SVG/PNG preview |
| Architecture HTML | Explaining how systems connect | Standalone HTML with inline SVG and export controls; PNG preview |

All three were visually reviewed. D2 was compiled with version 0.9.0 and the ELK layout engine. Excalidraw JSON was validated with Python's JSON parser. Its preview is generated from scene geometry, not exported by the Excalidraw application. The architecture template retains its pinned export libraries; core rendering works without JavaScript. PNG download was tested successfully in Chromium. Clipboard and PDF export were not exercised. External fonts and export libraries require network access.

The architecture option uses the requested dark technical style. Summary cards were removed to keep it short. The main guide uses the simpler light D2 view.

Rebuild: compile expert-flow.d2 to expert-flow-d2.svg and expert-flow-d2.png with `d2 --layout elk`, then run `node build-options.mjs` from this repository's environment.
