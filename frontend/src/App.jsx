import { useState, useRef, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const MODES = [
  {
    id: 'chat',
    label: 'Chat',
    description: 'General conversation with the LLM',
    endpoint: '/chat',
    color: '#2563eb',
  },
  {
    id: 'rag',
    label: 'Search Docs',
    description: 'Searches your docs/ folder before answering',
    endpoint: '/chat',
    color: '#7c3aed',
  },
  {
    id: 'agent',
    label: 'Agent',
    description: 'Uses tools — weather, calculator, doc search',
    endpoint: '/agent',
    color: '#059669',
  },
]

const SESSION_ID = 'session_' + Math.random().toString(36).slice(2, 8)

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [mode, setMode] = useState('chat')
  const [meta, setMeta] = useState(null)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)
  const [health, setHealth] = useState(null)

  const activeMode = MODES.find(m => m.id === mode)

  // auto scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // auto resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 200) + 'px'
  }, [input])

  // submit on Enter, newline on Shift+Enter
  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  async function handleSubmit() {
    const text = input.trim()
    if (!text || loading) return

    setError('')
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)

    try {
      const endpoint = activeMode.endpoint
      const payload = mode === 'rag'
        ? { message: text, session_id: SESSION_ID, use_rag: true }
        : mode === 'agent'
          ? { message: text, session_id: SESSION_ID }
          : { message: text, session_id: SESSION_ID, use_rag: false }

      const res = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail ?? 'Request failed')

      setMeta({ provider: data.provider, model: data.model })
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function clearSession() {
    await fetch(`${API_URL}/session/${SESSION_ID}`, { method: 'DELETE' })
    setMessages([])
    setMeta(null)
    setError('')
  }
  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then(r => r.json())
      .then(setHealth)
      .catch(() => { })
  }, [])

  return (
    <div style={styles.shell}>

      {/* sidebar */}
      <aside style={styles.sidebar}>
        <div style={styles.sidebarTop}>
          <p style={styles.sidebarTitle}>LangChain App</p>

          <button style={styles.newChat} onClick={clearSession}>
            + New chat
          </button>

          <p style={styles.sectionLabel}>Mode</p>

          {MODES.map(m => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              style={{
                ...styles.modeBtn,
                background: mode === m.id ? '#1e1e1e' : 'transparent',
                borderLeft: mode === m.id
                  ? `3px solid ${m.color}`
                  : '3px solid transparent',
              }}
            >
              <span style={{ ...styles.modeDot, background: m.color }} />
              <span>
                <span style={styles.modeLabel}>{m.label}</span>
                <span style={styles.modeDesc}>{m.description}</span>
              </span>
            </button>
          ))}
        </div>

        {/* mode info box */}
        <div style={styles.infoBox}>
          <p style={styles.infoTitle}>How to use</p>
          {mode === 'chat' && (
            <p style={styles.infoText}>
              General chat. Ask anything. The LLM answers from its training data only.
            </p>
          )}
          {mode === 'rag' && (
            <p style={styles.infoText}>
              Searches your <code style={styles.code}>docs/</code> folder first, then answers.
              Try: <em>"what endpoints does our API have?"</em>
            </p>
          )}
          {mode === 'agent' && (
            <p style={styles.infoText}>
              Has 3 tools it picks automatically:
              <br />• <strong>search_docs</strong> — your docs
              <br />• <strong>get_weather</strong> — any city
              <br />• <strong>calculator</strong> — any math
            </p>
          )}
          {meta && (
            <p style={styles.metaText}>
              {meta.provider} · {meta.model}
            </p>
          )}
          {health && (
            <div style={{ marginTop: 12, borderTop: '1px solid #1e1e1e', paddingTop: 10 }}>
              <p style={{ fontSize: 11, color: '#555', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                LangSmith
              </p>
              <p style={{ fontSize: 12, color: health.langsmith_tracing ? '#4ade80' : '#f87171' }}>
                {health.langsmith_tracing ? '● Tracing active' : '● Tracing off'}
              </p>
              {health.langsmith_tracing && (
                <p style={{ fontSize: 11, color: '#555', marginTop: 4 }}>
                  Project: {health.langsmith_project}
                </p>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* main chat area */}
      <main style={styles.main}>

        {/* empty state */}
        {messages.length === 0 && (
          <div style={styles.emptyState}>
            <p style={styles.emptyTitle}>
              {mode === 'chat' && 'What can I help with?'}
              {mode === 'rag' && 'Ask about your documents'}
              {mode === 'agent' && 'I have tools — try me'}
            </p>
            <p style={styles.emptySubtitle}>{activeMode.description}</p>

            {/* example prompts */}
            <div style={styles.examples}>
              {mode === 'chat' && (
                <>
                  <ExampleBtn onClick={setInput} text="Explain LangChain in simple words" />
                  <ExampleBtn onClick={setInput} text="What is the difference between RAG and fine-tuning?" />
                  <ExampleBtn onClick={setInput} text="How does memory work in LangChain?" />
                </>
              )}
              {mode === 'rag' && (
                <>
                  <ExampleBtn onClick={setInput} text="What endpoints does our chat API have?" />
                  <ExampleBtn onClick={setInput} text="What is our frontend tech stack?" />
                  <ExampleBtn onClick={setInput} text="How does our app use LangChain?" />
                </>
              )}
              {mode === 'agent' && (
                <>
                  <ExampleBtn onClick={setInput} text="What is the weather in Delhi?" />
                  <ExampleBtn onClick={setInput} text="Calculate 245 * 18 + 300" />
                  <ExampleBtn onClick={setInput} text="What endpoints does our API have?" />
                </>
              )}
            </div>
          </div>
        )}

        {/* messages */}
        <div style={styles.messages}>
          {messages.map((msg, i) => (
            <div
              key={i}
              style={{
                ...styles.msgRow,
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              {msg.role === 'assistant' && (
                <div style={{ ...styles.avatar, background: activeMode.color }}>
                  AI
                </div>
              )}
              <div
                style={{
                  ...styles.bubble,
                  background: msg.role === 'user' ? '#2f2f2f' : '#1a1a1a',
                  borderColor: msg.role === 'user' ? '#3f3f3f' : '#2a2a2a',
                  maxWidth: msg.role === 'user' ? '70%' : '80%',
                }}
              >
                <p style={styles.bubbleText}>{msg.content}</p>
              </div>
              {msg.role === 'user' && (
                <div style={{ ...styles.avatar, background: '#3f3f3f' }}>
                  You
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div style={{ ...styles.msgRow, justifyContent: 'flex-start' }}>
              <div style={{ ...styles.avatar, background: activeMode.color }}>AI</div>
              <div style={{ ...styles.bubble, background: '#1a1a1a', borderColor: '#2a2a2a' }}>
                <p style={{ ...styles.bubbleText, color: '#666' }}>Thinking...</p>
              </div>
            </div>
          )}

          {error && (
            <div style={styles.errorBanner}>
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* input bar */}
        <div style={styles.inputBar}>
          <div style={{ ...styles.inputWrap, borderColor: activeMode.color + '55' }}>

            {/* mode pill */}
            <span style={{ ...styles.modePill, background: activeMode.color + '22', color: activeMode.color }}>
              {activeMode.label}
            </span>

            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                mode === 'chat' ? 'Ask anything...' :
                  mode === 'rag' ? 'Ask about your docs...' :
                    'Ask me to use weather, calculator, or search docs...'
              }
              style={styles.textarea}
            />

            <button
              onClick={handleSubmit}
              disabled={loading || !input.trim()}
              style={{
                ...styles.sendBtn,
                background: loading || !input.trim() ? '#2a2a2a' : activeMode.color,
                cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? '...' : '↑'}
            </button>
          </div>
          <p style={styles.hint}>Enter to send · Shift+Enter for new line</p>
        </div>

      </main>
    </div>
  )
}

function ExampleBtn({ text, onClick }) {
  return (
    <button style={styles.exampleBtn} onClick={() => onClick(text)}>
      {text}
    </button>
  )
}

const styles = {
  shell: {
    display: 'flex',
    height: '100vh',
    background: '#0a0a0a',
    color: '#e5e5e5',
    fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
    overflow: 'hidden',
  },
  sidebar: {
    width: 260,
    minWidth: 260,
    background: '#111',
    borderRight: '1px solid #1e1e1e',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    padding: '16px 0',
    overflow: 'hidden',
  },
  sidebarTop: {
    padding: '0 12px',
  },
  sidebarTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: '#e5e5e5',
    margin: '0 0 16px',
    padding: '0 4px',
  },
  newChat: {
    width: '100%',
    padding: '8px 12px',
    background: '#1e1e1e',
    border: '1px solid #2a2a2a',
    borderRadius: 8,
    color: '#e5e5e5',
    fontSize: 13,
    cursor: 'pointer',
    textAlign: 'left',
    marginBottom: 20,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: '#555',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    margin: '0 0 8px 4px',
  },
  modeBtn: {
    width: '100%',
    display: 'flex',
    alignItems: 'flex-start',
    gap: 10,
    padding: '10px 12px',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    color: '#e5e5e5',
    textAlign: 'left',
    marginBottom: 4,
    transition: 'background 0.15s',
  },
  modeDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    marginTop: 5,
    flexShrink: 0,
  },
  modeLabel: {
    display: 'block',
    fontSize: 13,
    fontWeight: 500,
    color: '#e5e5e5',
  },
  modeDesc: {
    display: 'block',
    fontSize: 11,
    color: '#666',
    marginTop: 2,
    lineHeight: 1.4,
  },
  infoBox: {
    margin: '0 12px 8px',
    padding: '12px',
    background: '#161616',
    border: '1px solid #1e1e1e',
    borderRadius: 8,
  },
  infoTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: '#555',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    margin: '0 0 8px',
  },
  infoText: {
    fontSize: 12,
    color: '#888',
    lineHeight: 1.6,
    margin: 0,
  },
  code: {
    background: '#2a2a2a',
    padding: '1px 5px',
    borderRadius: 4,
    fontSize: 11,
    color: '#aaa',
  },
  metaText: {
    fontSize: 11,
    color: '#444',
    marginTop: 10,
    borderTop: '1px solid #1e1e1e',
    paddingTop: 8,
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  emptyState: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 24px',
  },
  emptyTitle: {
    fontSize: 26,
    fontWeight: 600,
    color: '#e5e5e5',
    margin: '0 0 8px',
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#666',
    margin: '0 0 32px',
  },
  examples: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    width: '100%',
    maxWidth: 520,
  },
  exampleBtn: {
    padding: '12px 16px',
    background: '#161616',
    border: '1px solid #2a2a2a',
    borderRadius: 10,
    color: '#aaa',
    fontSize: 13,
    cursor: 'pointer',
    textAlign: 'left',
    transition: 'border-color 0.15s, color 0.15s',
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '24px 10%',
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  msgRow: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 10,
  },
  avatar: {
    width: 28,
    height: 28,
    borderRadius: 6,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 10,
    fontWeight: 700,
    color: '#fff',
    flexShrink: 0,
  },
  bubble: {
    padding: '12px 16px',
    borderRadius: 12,
    border: '1px solid',
  },
  bubbleText: {
    fontSize: 14,
    lineHeight: 1.7,
    margin: 0,
    color: '#e5e5e5',
    whiteSpace: 'pre-wrap',
  },
  errorBanner: {
    padding: '10px 14px',
    background: '#2a1111',
    border: '1px solid #5a2020',
    borderRadius: 8,
    fontSize: 13,
    color: '#f87171',
  },
  inputBar: {
    padding: '12px 10% 16px',
    borderTop: '1px solid #1a1a1a',
  },
  inputWrap: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 8,
    background: '#161616',
    border: '1px solid',
    borderRadius: 14,
    padding: '8px 8px 8px 12px',
  },
  modePill: {
    fontSize: 11,
    fontWeight: 600,
    padding: '3px 8px',
    borderRadius: 20,
    whiteSpace: 'nowrap',
    alignSelf: 'flex-end',
    marginBottom: 4,
  },
  textarea: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: '#e5e5e5',
    fontSize: 14,
    lineHeight: 1.6,
    resize: 'none',
    maxHeight: 200,
    fontFamily: 'inherit',
  },
  sendBtn: {
    width: 32,
    height: 32,
    borderRadius: 8,
    border: 'none',
    color: '#fff',
    fontSize: 16,
    flexShrink: 0,
    alignSelf: 'flex-end',
    transition: 'background 0.15s',
  },
  hint: {
    fontSize: 11,
    color: '#333',
    margin: '6px 0 0 4px',
  },
}