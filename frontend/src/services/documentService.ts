import api from '@/api/axiosInstance'
import type { DocumentUploadResponse } from '@/types/api'

const MAX_PDF_BYTES = 10 * 1024 * 1024

export function validatePdfFile(file: File): string | null {
  const isPdf =
    file.type === 'application/pdf' ||
    file.name.toLowerCase().endsWith('.pdf')

  if (!isPdf) {
    return 'Only PDF files are supported.'
  }
  if (file.size === 0) {
    return 'The selected file is empty.'
  }
  if (file.size > MAX_PDF_BYTES) {
    return 'PDF must be 10 MB or smaller.'
  }
  return null
}

export const documentService = {
  /**
   * POST /documents/upload
   * Form fields: file (UploadFile), jurisdiction (required), title (optional)
   */
  async upload(
    file: File,
    jurisdiction: string,
    title?: string,
  ): Promise<DocumentUploadResponse> {
    const validationError = validatePdfFile(file)
    if (validationError) {
      throw new Error(validationError)
    }
    if (!jurisdiction.trim()) {
      throw new Error('Select a jurisdiction before uploading.')
    }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('jurisdiction', jurisdiction)
    if (title?.trim()) {
      formData.append('title', title.trim())
    }

    // Upload + PDF parse + embed can exceed the default 30s timeout.
    const res = await api.post<DocumentUploadResponse>(
      '/documents/upload',
      formData,
      { timeout: 180_000 },
    )
    return res.data
  },
}
