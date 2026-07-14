import { jsPDF } from 'jspdf'
import type { AnalyzeResponse, AnalysisHistory } from '@/types/api'

function wrapText(doc: jsPDF, text: string, x: number, y: number, maxWidth: number, lineHeight = 6): number {
  const lines = doc.splitTextToSize(text, maxWidth) as string[]
  for (const line of lines) {
    doc.text(line, x, y)
    y += lineHeight
  }
  return y
}

/** Download a PDF report for a live analysis result. */
export function exportAnalysisPdf(result: AnalyzeResponse, createdAt?: string): void {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  const margin = 16
  const maxWidth = 210 - margin * 2
  let y = 20

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(16)
  doc.text('LexAI Compliance Analysis Report', margin, y)
  y += 10

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10)
  doc.setTextColor(80)
  if (createdAt) {
    y = wrapText(doc, `Generated: ${createdAt}`, margin, y, maxWidth)
    y += 2
  }
  y = wrapText(doc, `Query: ${result.query}`, margin, y, maxWidth)
  y += 2
  y = wrapText(doc, `Product / feature: ${result.product_feature}`, margin, y, maxWidth)
  y += 6

  doc.setTextColor(0)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(12)
  doc.text('Summary scores', margin, y)
  y += 7
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10)
  const score =
    typeof result.compliance_score === 'number'
      ? result.compliance_score
      : '—'
  y = wrapText(
    doc,
    `Compliance score: ${score}  ·  Risk level: ${result.risk_level ?? 'n/a'}`,
    margin,
    y,
    maxWidth,
  )
  y += 6

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(12)
  doc.text('Jurisdictions', margin, y)
  y += 7
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10)
  const byJ = result.cross_jurisdiction?.by_jurisdiction ?? {}
  for (const [code, entry] of Object.entries(byJ)) {
    const stance = typeof entry === 'object' && entry && 'stance' in entry
      ? String((entry as { stance: string }).stance)
      : JSON.stringify(entry)
    y = wrapText(doc, `${code}: ${stance}`, margin, y, maxWidth)
    if (y > 270) {
      doc.addPage()
      y = 20
    }
  }
  y += 4

  if (result.cross_jurisdiction?.divergence_summary) {
    doc.setFont('helvetica', 'bold')
    doc.text('Divergence', margin, y)
    y += 6
    doc.setFont('helvetica', 'normal')
    y = wrapText(doc, result.cross_jurisdiction.divergence_summary, margin, y, maxWidth)
    y += 4
  }

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(12)
  doc.text('LLM answer', margin, y)
  y += 7
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10)
  const answer = result.llm?.answer_text || 'No LLM summary returned.'
  y = wrapText(doc, answer, margin, y, maxWidth)
  y += 6

  if (y > 250) {
    doc.addPage()
    y = 20
  }

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(12)
  doc.text('Risk scores', margin, y)
  y += 7
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10)
  for (const risk of result.risk_scores ?? []) {
    y = wrapText(
      doc,
      `${risk.jurisdiction}: ${risk.level} (${(risk.score * 100).toFixed(0)}%) — ${(risk.factors ?? []).join(', ') || 'n/a'}`,
      margin,
      y,
      maxWidth,
    )
    if (y > 270) {
      doc.addPage()
      y = 20
    }
  }
  y += 6

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(12)
  doc.text('Citations', margin, y)
  y += 7
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(9)
  for (const c of (result.citations ?? []).slice(0, 12)) {
    y = wrapText(
      doc,
      `[${c.citation_id}] ${c.source_label} (${c.jurisdiction}) — ${c.excerpt}`,
      margin,
      y,
      maxWidth,
      5,
    )
    y += 2
    if (y > 270) {
      doc.addPage()
      y = 20
    }
  }

  doc.setFontSize(8)
  doc.setTextColor(120)
  doc.text('LexAI — for informational / educational use. Not legal advice.', margin, 287)

  const safeName = result.query.slice(0, 40).replace(/[^\w\s-]/g, '').trim() || 'analysis'
  doc.save(`lexai-${safeName}.pdf`)
}

/** Lightweight PDF from history list row fields (Reports page). */
export function exportHistoryRowPdf(row: AnalysisHistory): void {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  const margin = 16
  let y = 20
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(16)
  doc.text('LexAI Analysis Summary', margin, y)
  y += 12
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(11)
  y = wrapText(doc, `Query: ${row.query}`, margin, y, 178)
  y += 4
  y = wrapText(doc, `Jurisdiction: ${row.jurisdiction}`, margin, y, 178)
  y += 4
  y = wrapText(doc, `Compliance score: ${row.compliance_score}`, margin, y, 178)
  y += 4
  y = wrapText(doc, `Risk level: ${row.risk_level}`, margin, y, 178)
  y += 4
  y = wrapText(doc, `Created: ${row.created_at}`, margin, y, 178)
  doc.setFontSize(8)
  doc.setTextColor(120)
  doc.text('LexAI — for informational / educational use. Not legal advice.', margin, 287)
  doc.save(`lexai-history-${row.id}.pdf`)
}
