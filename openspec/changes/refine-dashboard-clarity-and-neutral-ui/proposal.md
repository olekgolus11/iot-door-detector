# Dashboard Clarity And Neutral UI

## Summary
Refine the operator dashboard so the occupancy trend chart is self-explanatory and the overall interface moves from expressive/stylized toward a more neutral, calm, presentation-friendly visual language. The change adds explicit chart axes and labels, rebalances the information hierarchy, and redesigns the UI with a restrained, professional aesthetic.

## Why
The current dashboard is functionally useful, but two usability issues remain:
- the occupancy trend line does not clearly explain what is plotted on the Y axis
- the visual design feels too opinionated and distracts from the data during demos

For a class presentation, the interface should feel clear, neutral, and trustworthy before it feels decorative.

## Goals
- Make the occupancy trend chart explicitly readable without prior context.
- Show Y-axis meaning and visible values on the occupancy chart.
- Redesign the dashboard toward a more neutral, calm, and professional tone.
- Preserve the current operator workflow, debug route, and chart-rich information architecture.
- Improve visual consistency so the dashboard feels like a coherent tool rather than a prototype.

## Non-Goals
- Reworking the underlying backend control-state logic.
- Removing charts or reducing the dashboard back to raw tables.
- Rebranding the entire project with a flashy new visual identity.
- Changing the data model or MQTT architecture.

## Scope
This change is focused on frontend clarity and presentation quality. It affects chart rendering, chart annotation, spacing and typography, color and background treatment, card styling, and overall visual hierarchy across the main dashboard and debug page. It may include small API-shape adjustments only if needed to make the chart annotations accurate and maintainable.

## Success Criteria
- The occupancy trend chart clearly communicates that the Y axis represents people currently counted in the room.
- The chart includes visible Y-axis values or ticks so viewers can read the scale directly.
- The main dashboard uses a more neutral, less stylized visual system while remaining polished.
- The debug page stays functional and visually aligned with the calmer design direction.
- Existing dashboard features remain intact: operator controls, analytics, recent events, and debug filtering.

## Risks
- A more neutral UI can become bland if the redesign is too generic or timid.
- Adding chart labels and axes can clutter the layout if spacing is not adjusted carefully.
- If the visual reset is only partial, the product can end up looking inconsistent across pages.

## Additional Ideas
- Add small chart subtitles that explain whether data is “current room count,” “entries per bucket,” or “door totals.”
- Use subtle legends or axis titles where meaning is not obvious at first glance.
- Add a compact “last updated” indicator near live charts to reinforce trust in the data.
