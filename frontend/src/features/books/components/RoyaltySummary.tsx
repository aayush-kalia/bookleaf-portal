
import type { RoyaltySummary as RoyaltySummaryType } from '../types'

interface Props {
  summary: RoyaltySummaryType
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(value)
}

export function RoyaltySummary({ summary }: Props) {
  const metrics = [
    { label: 'Total earned', value: summary.total_earned },
    { label: 'Total paid', value: summary.total_paid },
    { label: 'Pending royalties', value: summary.total_pending },
  ]

  return (
    <section className="royalty-grid" aria-label="Royalty summary">
      {metrics.map((metric) => (
        <article className="royalty-card" key={metric.label}>
          <p className="muted">{metric.label}</p>
          <h2>{formatCurrency(metric.value)}</h2>
        </article>
      ))}
    </section>
  )
}
