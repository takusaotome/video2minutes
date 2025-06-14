<template>
  <div class="markdown-renderer">
    <!-- Table of Contents (if enabled) -->
    <div
      v-if="showToc && tableOfContents.length > 0"
      class="markdown-toc-wrapper"
    >
      <Card class="toc-card">
        <template #title>
          <div class="toc-header">
            <i class="pi pi-list"></i>
            目次
          </div>
        </template>
        <template #content>
          <nav class="markdown-toc">
            <ul class="toc-list">
              <li
                v-for="heading in tableOfContents"
                :key="heading.id"
                :class="`toc-item toc-level-${heading.level}`"
              >
                <a
                  :href="`#${heading.id}`"
                  class="toc-link"
                  @click.prevent="scrollToHeading(heading.id)"
                >
                  {{ heading.text }}
                </a>
              </li>
            </ul>
          </nav>
        </template>
      </Card>
    </div>

    <!-- Markdown Content -->
    <div class="markdown-content-wrapper">
      <Card class="markdown-card">
        <template #content>
          <div
            class="markdown-content"
            :class="{ 'with-toc': showToc && tableOfContents.length > 0 }"
            v-html="renderedContent"
          ></div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import Card from 'primevue/card'
import {
  parseMarkdown,
  extractTableOfContents,
  getMarkdownWordCount
} from '@/utils/markdown'

export default {
  name: 'MarkdownRenderer',
  components: {
    Card
  },
  props: {
    content: {
      type: String,
      default: ''
    },
    showToc: {
      type: Boolean,
      default: true
    },
    enableSyntaxHighlight: {
      type: Boolean,
      default: true
    }
  },
  emits: ['word-count'],
  setup(props, { emit }) {
    const renderedContent = ref('')
    const tableOfContents = ref([])

    const processContent = () => {
      if (!props.content) {
        renderedContent.value = ''
        tableOfContents.value = []
        emit('word-count', 0)
        return
      }

      try {
        // Parse markdown to HTML
        renderedContent.value = parseMarkdown(props.content, {
          enableSyntaxHighlight: props.enableSyntaxHighlight
        })

        // Extract table of contents
        if (props.showToc) {
          tableOfContents.value = extractTableOfContents(props.content)
        }

        // Emit word count
        const wordCount = getMarkdownWordCount(props.content)
        emit('word-count', wordCount)
      } catch (error) {
        console.error('Failed to process markdown content:', error)
        renderedContent.value =
          '<p class="markdown-error">コンテンツの処理に失敗しました</p>'
        tableOfContents.value = []
        emit('word-count', 0)
      }
    }

    const scrollToHeading = headingId => {
      const element = document.getElementById(headingId)
      if (element) {
        element.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        })

        // Add highlight effect
        element.classList.add('heading-highlight')
        setTimeout(() => {
          element.classList.remove('heading-highlight')
        }, 2000)
      }
    }

    // Watch for content changes
    watch(() => props.content, processContent, { immediate: true })

    onMounted(() => {
      processContent()
    })

    return {
      renderedContent,
      tableOfContents,
      scrollToHeading
    }
  }
}
</script>

<style scoped>
.markdown-renderer {
  display: flex;
  gap: 2rem;
  max-width: 100%;
}

.markdown-toc-wrapper {
  flex: 0 0 280px;
  position: sticky;
  top: 2rem;
  height: fit-content;
  max-height: calc(100vh - 4rem);
  overflow-y: auto;
}

.toc-card {
  border: 1px solid var(--gray-200);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.toc-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--gray-550);
  font-size: 1rem;
  font-weight: 600;
}

.markdown-toc {
  max-height: 400px;
  overflow-y: auto;
}

.toc-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.toc-item {
  margin: 0;
  padding: 0;
}

.toc-item.toc-level-1 {
  margin-left: 0;
}

.toc-item.toc-level-2 {
  margin-left: 1rem;
}

.toc-item.toc-level-3 {
  margin-left: 2rem;
}

.toc-item.toc-level-4 {
  margin-left: 3rem;
}

.toc-item.toc-level-5 {
  margin-left: 4rem;
}

.toc-item.toc-level-6 {
  margin-left: 5rem;
}

.toc-link {
  display: block;
  padding: 0.5rem 0;
  color: var(--gray-500);
  text-decoration: none;
  font-size: 0.9rem;
  line-height: 1.4;
  border-left: 2px solid transparent;
  padding-left: 0.75rem;
  margin-left: -0.75rem;
  transition: all 0.2s ease;
}

.toc-link:hover {
  color: var(--brand-500);
  border-left-color: var(--brand-500);
  background-color: rgba(102, 126, 234, 0.05);
}

.markdown-content-wrapper {
  flex: 1;
  min-width: 0;
}

.markdown-card {
  border: 1px solid var(--gray-200);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* Responsive */
@media (max-width: 1024px) {
  .markdown-renderer {
    flex-direction: column;
    gap: 1rem;
  }

  .markdown-toc-wrapper {
    flex: none;
    position: static;
    max-height: 300px;
  }
}

@media (max-width: 768px) {
  .markdown-renderer {
    gap: 0.5rem;
  }

  .markdown-toc-wrapper {
    max-height: 200px;
  }
}
</style>

<!-- Global styles for markdown content -->
<style>
/* Markdown Content Styles */
.markdown-content {
  font-family:
    -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.7;
  color: var(--gray-700);
  max-width: none;
}

.markdown-content.with-toc {
  padding-left: 1rem;
}

/* Headings */
.markdown-heading {
  color: var(--gray-800);
  font-weight: 700;
  margin: 2rem 0 1rem 0;
  line-height: 1.3;
  position: relative;
  scroll-margin-top: 2rem;
}

.markdown-h1 {
  font-size: 2.25rem;
  border-bottom: 3px solid var(--gray-200);
  padding-bottom: 0.75rem;
  margin-bottom: 1.5rem;
}

.markdown-h2 {
  font-size: 1.875rem;
  border-bottom: 2px solid var(--gray-100);
  padding-bottom: 0.5rem;
  margin-top: 2.5rem;
}

.markdown-h3 {
  font-size: 1.5rem;
  margin-top: 2rem;
}

.markdown-h4 {
  font-size: 1.25rem;
}

.markdown-h5 {
  font-size: 1.125rem;
}

.markdown-h6 {
  font-size: 1rem;
  color: var(--gray-500);
}

.heading-highlight {
  background-color: rgba(255, 235, 59, 0.3) !important;
  padding: 0.5rem !important;
  border-radius: 4px !important;
  transition: background-color 2s ease-out !important;
}

/* Paragraphs */
.markdown-paragraph {
  margin: 1rem 0;
  line-height: 1.7;
}

/* Lists */
.markdown-list {
  margin: 1rem 0;
  padding-left: 2rem;
}

.markdown-ul {
  list-style-type: disc;
}

.markdown-ol {
  list-style-type: decimal;
}

.markdown-list-item {
  margin: 0.5rem 0;
  line-height: 1.6;
}

.markdown-list .markdown-list {
  margin: 0.5rem 0;
}

/* Blockquotes */
.markdown-blockquote {
  margin: 1.5rem 0;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, var(--gray-600-light) 0%, var(--gray-650-light) 100%);
  border-radius: 8px;
  position: relative;
  border-left: 4px solid var(--brand-500);
}

.blockquote-indicator {
  position: absolute;
  left: -2px;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(135deg, var(--brand-500) 0%, var(--brand-700) 100%);
  border-radius: 2px;
}

.blockquote-content {
  color: var(--gray-600);
  font-style: italic;
  font-size: 1.05rem;
}

.blockquote-content .markdown-paragraph:last-child {
  margin-bottom: 0;
}

/* Code */
.markdown-inline-code {
  background: var(--gray-100);
  color: var(--warning-600);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.9em;
  font-weight: 500;
}

.markdown-code-block {
  margin: 1.5rem 0;
  border-radius: 8px;
  overflow: hidden;
  background: var(--gray-800);
  border: 1px solid var(--gray-700);
}

.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--gray-700);
  border-bottom: 1px solid var(--gray-600);
}

.code-language {
  color: var(--gray-300);
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: uppercase;
}

.code-copy-btn {
  background: var(--gray-600);
  color: var(--gray-300);
  border: none;
  padding: 0.375rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.code-copy-btn:hover {
  background: var(--gray-500);
  color: white;
}

.code-copy-btn.copied {
  background: var(--success-600);
  color: white;
}

.code-content {
  margin: 0;
  padding: 1rem;
  background: var(--gray-800);
  color: var(--gray-50);
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.9rem;
  line-height: 1.5;
  overflow-x: auto;
}

.code-content code {
  background: none;
  color: inherit;
  padding: 0;
  border-radius: 0;
}

/* Tables */
.markdown-table-wrapper {
  margin: 1.5rem 0;
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid var(--gray-200);
}

.markdown-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.markdown-table-header {
  background: var(--gray-50);
}

.markdown-table th,
.markdown-table td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--gray-200);
}

.markdown-table th {
  font-weight: 600;
  color: var(--gray-700);
}

.markdown-table tbody tr:hover {
  background: var(--gray-50);
}

.markdown-table tbody tr:last-child td {
  border-bottom: none;
}

/* Text formatting */
.markdown-strong {
  font-weight: 700;
  color: var(--gray-800);
}

.markdown-emphasis {
  font-style: italic;
  color: var(--gray-600);
}

/* Links */
.markdown-link {
  color: var(--brand-500);
  text-decoration: none;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  transition: all 0.2s ease;
}

.markdown-link:hover {
  color: var(--brand-400);
  text-decoration: underline;
}

.markdown-link i {
  font-size: 0.8em;
  opacity: 0.7;
}

/* Horizontal rule */
.markdown-divider {
  margin: 2rem 0;
  text-align: center;
}

.markdown-divider hr {
  border: none;
  height: 2px;
  background: linear-gradient(to right, transparent, var(--gray-200), transparent);
  margin: 0;
}

/* Error state */
.markdown-error {
  color: var(--error-600);
  background: var(--error-50);
  border: 1px solid var(--error-100);
  border-radius: 6px;
  padding: 1rem;
  font-weight: 500;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .markdown-h1 {
    font-size: 1.875rem;
  }

  .markdown-h2 {
    font-size: 1.5rem;
  }

  .markdown-h3 {
    font-size: 1.25rem;
  }

  .markdown-list {
    padding-left: 1.5rem;
  }

  .markdown-blockquote {
    padding: 0.75rem 1rem;
    margin: 1rem 0;
  }

  .code-header {
    padding: 0.5rem 0.75rem;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .code-content {
    padding: 0.75rem;
    font-size: 0.8rem;
  }

  .markdown-table-wrapper {
    font-size: 0.8rem;
  }

  .markdown-table th,
  .markdown-table td {
    padding: 0.5rem 0.75rem;
  }
}
</style>
