import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('highlight.js', () => ({
  default: {
    getLanguage: () => true,
    highlight: () => ({ value: 'hl' })
  }
}))

vi.mock('dompurify', () => ({
  default: { sanitize: vi.fn(html => html) }
}))

vi.mock('marked', () => {
  const lexer = md => {
    const tokens = []
    const regex = /^(#{1,6})\s*(.+)$/gm
    let match
    while ((match = regex.exec(md))) {
      tokens.push({ type: 'heading', depth: match[1].length, text: match[2] })
    }
    return tokens
  }
  const parse = vi.fn(md => `<p>${md}</p>`)
  const setOptions = vi.fn()
  return { marked: { Renderer: class {}, lexer, parse, setOptions } }
})

import { parseMarkdown, extractTableOfContents, getMarkdownWordCount } from '@/utils/markdown'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

describe('markdown utils', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('parses markdown and sanitizes result', () => {
    const html = parseMarkdown('**bold**')
    expect(marked.parse).toHaveBeenCalledWith('**bold**')
    expect(DOMPurify.default.sanitize).toHaveBeenCalled()
    expect(html).toBe('<p>**bold**</p>')
  })

  it('extracts table of contents', () => {
    const md = '# Title\n\n## Section 1\nText\n### SubSection\nMore'
    const toc = extractTableOfContents(md)
    expect(toc).toEqual([
      { level: 1, text: 'Title', id: 'title' },
      { level: 2, text: 'Section 1', id: 'section-1' },
      { level: 3, text: 'SubSection', id: 'subsection' }
    ])
  })

  it('counts words from markdown', () => {
    const count = getMarkdownWordCount('これは**テスト**です')
    expect(count).toBe(9)
  })
})
