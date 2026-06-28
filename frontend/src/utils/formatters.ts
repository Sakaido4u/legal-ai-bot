// Utility functions for formatting data displayed in the UI.
// Keep ALL formatting logic here — never format inline in components.

import { format, formatDistanceToNow } from 'date-fns'

// Format ISO date string → "Jun 10, 2025"
export function formatDate(isoString: string): string {
  try {
    return format(new Date(isoString), 'MMM d, yyyy')
  } catch {
    return 'Invalid date'
  }
}

// Format ISO date string → "2 days ago"
export function formatRelative(isoString: string): string {
  try {
    return formatDistanceToNow(new Date(isoString), { addSuffix: true })
  } catch {
    return 'Unknown'
  }
}

// Format compliance score → color class
export function scoreToColor(score: number): string {
  if (score >= 80) return 'text-green-600 dark:text-green-400'
  if (score >= 60) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

// Format compliance score → label
export function scoreToLabel(score: number): string {
  if (score >= 80) return 'Compliant'
  if (score >= 60) return 'Partial'
  return 'Non-Compliant'
}

// Format milliseconds → "2.3s"
export function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

// Truncate long text
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '…'
}