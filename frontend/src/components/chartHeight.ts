/**
 * Shared by the chart and its loading placeholder.
 *
 * They must agree exactly: `ResponsiveContainer` needs a sized parent, and if
 * the skeleton were a different height the card would jump when the lazy chunk
 * arrives.
 */
export const CHART_HEIGHT = 56
