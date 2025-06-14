import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js'

// Configure marked with custom renderer
const renderer = new marked.Renderer()

// Custom heading renderer with anchors
renderer.heading = function (text, level) {
  const id = text.toLowerCase().replace(/[^\w]+/g, '-')
  return `<h${level} id="${id}" class="markdown-heading markdown-h${level}">
    <span class="heading-content">${text}</span>
  </h${level}>`
}

// Custom list renderer
renderer.list = function (body, ordered, start) {
  const type = ordered ? 'ol' : 'ul'
  const startatt = ordered && start !== 1 ? ` start="${start}"` : ''
  return `<${type}${startatt} class="markdown-list markdown-${type}">
    ${body}
  </${type}>`
}

// Custom list item renderer
renderer.listitem = function (text) {
  return `<li class="markdown-list-item">${text}</li>`
}

// Custom paragraph renderer
renderer.paragraph = function (text) {
  return `<p class="markdown-paragraph">${text}</p>`
}

// Custom blockquote renderer
renderer.blockquote = function (quote) {
  return `<blockquote class="markdown-blockquote">
    <div class="blockquote-indicator"></div>
    <div class="blockquote-content">${quote}</div>
  </blockquote>`
}

// Custom table renderer
renderer.table = function (header, body) {
  return `<div class="markdown-table-wrapper">
    <table class="markdown-table">
      <thead class="markdown-table-header">${header}</thead>
      <tbody class="markdown-table-body">${body}</tbody>
    </table>
  </div>`
}

// Custom code block renderer with syntax highlighting
renderer.code = function (code, language) {
  const validLanguage = hljs.getLanguage(language) ? language : 'plaintext'
  const highlighted = hljs.highlight(code, { language: validLanguage }).value

  return `<div class="markdown-code-block">
    <div class="code-header">
      <span class="code-language">${validLanguage}</span>
      <button class="code-copy-btn" onclick="copyCodeToClipboard(this)">
        <i class="pi pi-copy"></i>
        コピー
      </button>
    </div>
    <pre class="code-content"><code class="hljs language-${validLanguage}">${highlighted}</code></pre>
  </div>`
}

// Custom inline code renderer
renderer.codespan = function (code) {
  return `<code class="markdown-inline-code">${code}</code>`
}

// Custom strong renderer
renderer.strong = function (text) {
  return `<strong class="markdown-strong">${text}</strong>`
}

// Custom emphasis renderer
renderer.em = function (text) {
  return `<em class="markdown-emphasis">${text}</em>`
}

// Custom link renderer
renderer.link = function (href, title, text) {
  const titleAttr = title ? ` title="${title}"` : ''
  return `<a href="${href}"${titleAttr} class="markdown-link" target="_blank" rel="noopener noreferrer">
    ${text}
    <i class="pi pi-external-link"></i>
  </a>`
}

// Custom horizontal rule renderer
renderer.hr = function () {
  return '<div class="markdown-divider"><hr></div>'
}

// Configure marked options
marked.setOptions({
  renderer: renderer,
  highlight: function (code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext'
    return hljs.highlight(code, { language }).value
  },
  langPrefix: 'hljs language-',
  pedantic: false,
  gfm: true,
  breaks: true,
  sanitize: false,
  smartypants: true,
  xhtml: false
})

/**
 * Convert markdown to safe HTML
 * @param {string} markdown - The markdown text to convert
 * @param {object} options - Additional options
 * @returns {string} - Safe HTML string
 */
export function parseMarkdown(markdown, options = {}) {
  if (!markdown || typeof markdown !== 'string') {
    return ''
  }

  try {
    // Parse markdown to HTML
    let html = marked.parse(markdown)

    // Sanitize HTML to prevent XSS attacks
    html = DOMPurify.sanitize(html, {
      ALLOWED_TAGS: [
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'p',
        'br',
        'strong',
        'em',
        'u',
        's',
        'ul',
        'ol',
        'li',
        'blockquote',
        'table',
        'thead',
        'tbody',
        'tr',
        'td',
        'th',
        'pre',
        'code',
        'a',
        'hr',
        'div',
        'span',
        'i',
        'button'
      ],
      ALLOWED_ATTR: [
        'href',
        'title',
        'target',
        'rel',
        'class',
        'id',
        'start',
        'onclick'
      ],
      ALLOWED_URI_REGEXP:
        /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|cid|xmpp):|[^a-z]|[a-z+.-]+(?:[^a-z+.-:]|$))/i
    })

    return html
  } catch (error) {
    console.error('Failed to parse markdown:', error)
    return `<p class="markdown-error">マークダウンの解析に失敗しました</p>`
  }
}

/**
 * Extract table of contents from markdown
 * @param {string} markdown - The markdown text
 * @param {Object} options - Options for TOC generation
 * @returns {Array} - Array of heading objects
 */
export function extractTableOfContents(markdown, options = {}) {
  if (!markdown) return []

  const {
    excludeTexts = ['会議情報', 'Meeting Information', '会議概要'],
    minLevel = 1,
    maxLevel = 3
  } = options

  const headings = []
  const tokens = marked.lexer(markdown)

  tokens.forEach(token => {
    if (token.type === 'heading') {
      // Skip if level is outside the desired range
      if (token.depth < minLevel || token.depth > maxLevel) {
        return
      }
      
      // Skip if text matches excluded patterns
      const shouldExclude = excludeTexts.some(excludeText => 
        token.text.toLowerCase().includes(excludeText.toLowerCase())
      )
      
      if (shouldExclude) {
        return
      }

      const id = token.text.toLowerCase().replace(/[^\w]+/g, '-')
      headings.push({
        level: token.depth,
        text: token.text,
        id: id
      })
    }
  })

  return headings
}

/**
 * Get word count from markdown
 * @param {string} markdown - The markdown text
 * @returns {number} - Word count
 */
export function getMarkdownWordCount(markdown) {
  if (!markdown) return 0

  // Remove markdown syntax and count characters for Japanese
  const plainText = markdown
    .replace(/```[\s\S]*?```/g, '') // Remove code blocks
    .replace(/`[^`]*`/g, '') // Remove inline code
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // Remove links but keep text
    .replace(/[#*_~`>-]/g, '') // Remove markdown symbols
    .replace(/\s+/g, ' ') // Normalize whitespace
    .trim()

  return plainText.length
}

/**
 * Copy code block content to clipboard
 * @param {HTMLElement} button - The copy button element
 */
window.copyCodeToClipboard = function (button) {
  try {
    const codeBlock = button.closest('.markdown-code-block')
    const codeContent = codeBlock.querySelector('code').textContent

    navigator.clipboard
      .writeText(codeContent)
      .then(() => {
        const originalText = button.innerHTML
        button.innerHTML = '<i class="pi pi-check"></i> コピー済み'
        button.classList.add('copied')

        setTimeout(() => {
          button.innerHTML = originalText
          button.classList.remove('copied')
        }, 2000)
      })
      .catch(err => {
        console.error('Could not copy code: ', err)
      })
  } catch (error) {
    console.error('Failed to copy code:', error)
  }
}
