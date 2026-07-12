import { useState, useRef, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { sendMessage, addUserMessage } from '../store/chatSlice'
import './ChatPanel.css'

const TOOL_LABELS = {
  log_interaction: 'Logged interaction',
  edit_interaction: 'Edited interaction',
  get_interaction_history: 'Looked up history',
  schedule_follow_up: 'Scheduled follow-up',
  flag_compliance_risk: 'Ran compliance check',
}

export default function ChatPanel() {
  const dispatch = useDispatch()
  const messages = useSelector((s) => s.chat.messages)
  const status = useSelector((s) => s.chat.status)
  const activeInteractionId = useSelector((s) => s.interactions.draft.id)
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status])

  const handleSend = () => {
    if (!input.trim() || status === 'thinking') return
    dispatch(addUserMessage(input))
    dispatch(sendMessage({ message: input, activeInteractionId }))
    setInput('')
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="bot-avatar">🤖</span>
        <div>
          <div className="chat-title">AI Assistant</div>
          <div className="chat-subtitle">Log Interaction details here via chat</div>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role} ${m.isError ? 'error' : ''}`}>
            {m.text}
            {m.toolUsed && (
              <div className="tool-tag">✅ {TOOL_LABELS[m.toolUsed] || m.toolUsed}</div>
            )}
          </div>
        ))}
        {status === 'thinking' && <div className="bubble assistant thinking">Thinking…</div>}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          rows={1}
          placeholder="Describe Interaction..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
        />
        <button onClick={handleSend} disabled={status === 'thinking'}>
          A Log
        </button>
      </div>
    </div>
  )
}
