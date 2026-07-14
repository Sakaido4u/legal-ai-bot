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

export interface DocumentListResponse {
  documents: DocumentUploadResponse[]
  total: number
}

export interface DocumentSectionChunk {
  id: number
  chunk_index: number
  text: string
  word_count: number
  char_count: number
  vector_reference: string
}

export interface DocumentSection {
  id: number
  section_id: number
  heading: string | null
  numeric_id: string | null
  depth: number
  parent_id: number | null
  chunks: DocumentSectionChunk[]
}

export interface DocumentDetailResponse extends DocumentUploadResponse {
  source_url?: string | null
  sections?: DocumentSection[]
}

export interface DeleteDocumentResponse {
  id: number
  deleted: boolean
  message: string
}

export const documentService = {
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

    const res = await api.post<DocumentUploadResponse>(
      '/documents/upload',
      formData,
      { timeout: 180_000 },
    )
    return res.data
  },

  async list(skip = 0, limit = 100): Promise<DocumentListResponse> {
    const res = await api.get<DocumentListResponse>('/documents', {
      params: { skip, limit },
    })
    return res.data
  },

  async get(id: number): Promise<DocumentDetailResponse> {
    const res = await api.get<DocumentDetailResponse>(`/documents/${id}`)
    return res.data
  },

  async remove(id: number): Promise<DeleteDocumentResponse> {
    const res = await api.delete<DeleteDocumentResponse>(`/documents/${id}`, {
      timeout: 120_000,
    })
    return res.data
  },
}
