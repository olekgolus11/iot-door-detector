# Design: Dashboard Clarity And Neutral UI

## Current State
- The operator dashboard already includes charts, controls, and a separate debug page.
- The occupancy trend chart shows a line but does not explicitly label the measured quantity on the Y axis.
- The current visual design leans warm, layered, and somewhat expressive, which makes the UI feel less neutral than desired for a classroom tool.

## Proposed Solution
Treat this as a focused frontend refinement with two outputs:

1. Improve chart readability by adding explicit Y-axis labeling and tick values to the occupancy trend.
2. Redesign the overall interface around a neutral editorial/utilitarian aesthetic that feels calmer, cleaner, and more presentation-ready.

## Frontend Direction

### Aesthetic Choice
Use a neutral editorial/utilitarian direction:
- soft off-white or stone background
- restrained contrast
- disciplined spacing
- quiet accent usage
- professional, non-gimmicky card system

The design should still feel intentionally crafted, but the data should become the visual focal point rather than the decorative treatment.

### Typography
- Keep a distinctive but calmer pairing.
- Favor legible body typography and controlled display usage.
- Reserve serif or expressive typography for major headings only if it still feels neutral.
- Ensure chart labels and axis text are highly readable.

### Color System
- Shift toward neutral grays, stone tones, muted greens, and limited accent highlights.
- Remove the feeling of strong gradient-driven styling as the primary visual identity.
- Use accent color mainly for:
  - active state
  - chart lines
  - status emphasis

### Layout and Surfaces
- Keep the existing dashboard structure, but reduce visual noise:
  - simpler surface treatments
  - lighter shadows
  - more disciplined borders
  - less ornamental layering
- Improve whitespace and alignment so charts and controls feel easier to scan.

## Occupancy Trend Chart Changes
- Add an explicit Y-axis title such as `People in room`.
- Render visible Y-axis ticks based on the current chart range.
- Keep the X axis as time buckets, but make the Y axis unambiguous.
- Optionally add a small subtitle like `Current occupancy over time`.
- Ensure the SVG implementation remains lightweight and does not require a chart-library rewrite.

## Supporting UI Adjustments
- Bring the entries-vs-leaves and per-door charts into the same calmer visual system.
- Make chart containers more readable through:
  - clearer headings
  - quieter backgrounds
  - consistent label placement
- Align the debug page with the same neutral system so it does not feel like a different product.

## Files Likely Affected
- `frontend/src/components/Charts.jsx`
- `frontend/src/components/DashboardPage.jsx`
- `frontend/src/components/DebugPage.jsx`
- `frontend/src/styles.css`
- `frontend/index.html`

## Testing Strategy
- Manually verify that a first-time viewer can understand the occupancy trend chart without explanation.
- Manually verify the dashboard and debug page on desktop and mobile widths.
- If frontend tests are added later, ensure the occupancy chart renders axis labels and tick text for non-empty datasets.

## Open Questions Resolved For This Change
- The desired direction is more neutral, not more dramatic.
- The occupancy chart should remain custom SVG-based unless implementation friction makes that impractical.
- The redesign should preserve the current information architecture instead of rethinking the full product again.
