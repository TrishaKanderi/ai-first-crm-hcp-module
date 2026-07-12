import { useDispatch, useSelector } from 'react-redux'
import { useState } from 'react'
import { updateDraftField, addListItem, saveInteraction } from '../store/interactionsSlice'
import './InteractionForm.css'

const SENTIMENTS = [
  { key: 'Positive', emoji: '🙂' },
  { key: 'Neutral', emoji: '😐' },
  { key: 'Negative', emoji: '🙁' },
]

function Tag({ text }) {
  return <span className="tag">{text}</span>
}

export default function InteractionForm() {
  const dispatch = useDispatch()
  const draft = useSelector((s) => s.interactions.draft)
  const status = useSelector((s) => s.interactions.status)

  const [materialInput, setMaterialInput] = useState('')
  const [sampleInput, setSampleInput] = useState('')
  const [attendeeInput, setAttendeeInput] = useState('')

  const setField = (field) => (e) =>
    dispatch(updateDraftField({ field, value: e.target.value }))

  const addTag = (field, value, clear) => {
    if (!value.trim()) return
    dispatch(addListItem({ field, value: value.trim() }))
    clear('')
  }

  return (
    <div className="interaction-form">
      <div className="form-header">
        <h2>Log HCP Interaction</h2>
        {draft.id && <span className="pill">#{draft.id}</span>}
      </div>

      <div className="form-grid">
        <label className="field">
          <span>HCP Name</span>
          <input
            placeholder="Search or select HCP..."
            value={draft.hcp_name}
            onChange={setField('hcp_name')}
          />
        </label>

        <label className="field">
          <span>Interaction Type</span>
          <select value={draft.interaction_type} onChange={setField('interaction_type')}>
            <option>Meeting</option>
            <option>Call</option>
            <option>Email</option>
            <option>Conference</option>
          </select>
        </label>

        <label className="field">
          <span>Date</span>
          <input type="date" value={draft.interaction_date || ''} onChange={setField('interaction_date')} />
        </label>

        <label className="field">
          <span>Time</span>
          <input type="time" value={draft.interaction_time || ''} onChange={setField('interaction_time')} />
        </label>
      </div>

      <label className="field full">
        <span>Attendees</span>
        <div className="tag-input">
          <input
            placeholder="Enter names or search..."
            value={attendeeInput}
            onChange={(e) => setAttendeeInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('attendees', attendeeInput, setAttendeeInput))}
          />
        </div>
        <div className="tag-list">
          {draft.attendees?.map((a, i) => <Tag key={i} text={a} />)}
        </div>
      </label>

      <label className="field full">
        <span>Topics Discussed</span>
        <textarea
          rows={3}
          placeholder="Enter key discussion points..."
          value={draft.topics_discussed}
          onChange={setField('topics_discussed')}
        />
        <button type="button" className="link-btn" disabled title="Voice capture not wired up in this build">
          🎙 Summarize from Voice Note (Requires Consent)
        </button>
      </label>

      <div className="form-grid two">
        <label className="field">
          <span>Materials Shared</span>
          <div className="row-with-btn">
            <input
              placeholder="Brochures, leave-behinds..."
              value={materialInput}
              onChange={(e) => setMaterialInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('materials_shared', materialInput, setMaterialInput))}
            />
            <button type="button" onClick={() => addTag('materials_shared', materialInput, setMaterialInput)}>
              🔍 Search/Add
            </button>
          </div>
          <div className="tag-list">
            {draft.materials_shared?.length
              ? draft.materials_shared.map((m, i) => <Tag key={i} text={m} />)
              : <span className="muted">No materials added.</span>}
          </div>
        </label>

        <label className="field">
          <span>Samples Distributed</span>
          <div className="row-with-btn">
            <input
              placeholder="Sample / lot..."
              value={sampleInput}
              onChange={(e) => setSampleInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('samples_distributed', sampleInput, setSampleInput))}
            />
            <button type="button" onClick={() => addTag('samples_distributed', sampleInput, setSampleInput)}>
              + Add Sample
            </button>
          </div>
          <div className="tag-list">
            {draft.samples_distributed?.length
              ? draft.samples_distributed.map((m, i) => <Tag key={i} text={m} />)
              : <span className="muted">No samples added.</span>}
          </div>
        </label>
      </div>

      <label className="field full">
        <span>Observed / Inferred HCP Sentiment</span>
        <div className="sentiment-row">
          {SENTIMENTS.map((s) => (
            <label key={s.key} className="sentiment-option">
              <input
                type="radio"
                name="sentiment"
                checked={draft.sentiment === s.key}
                onChange={() => dispatch(updateDraftField({ field: 'sentiment', value: s.key }))}
              />
              <span>{s.emoji} {s.key}</span>
            </label>
          ))}
        </div>
      </label>

      <label className="field full">
        <span>Outcomes</span>
        <textarea
          rows={2}
          placeholder="Key outcomes or agreements..."
          value={draft.outcomes}
          onChange={setField('outcomes')}
        />
      </label>

      {draft.follow_up_actions?.length > 0 && (
        <div className="field full">
          <span>Follow-up Actions</span>
          <ul className="followups">
            {draft.follow_up_actions.map((f, i) => (
              <li key={i}>
                <strong>{f.note}</strong>
                {f.due_date ? <span className="muted"> · due {f.due_date}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      )}

      {draft.compliance_flags?.length > 0 && (
        <div className="compliance-banner">
          ⚠ {draft.compliance_flags.length} compliance flag(s) detected — review before submitting.
          <ul>
            {draft.compliance_flags.map((f, i) => (
              <li key={i}><strong>{f.type}</strong>: {f.detail} ({f.severity})</li>
            ))}
          </ul>
        </div>
      )}

      <div className="form-actions">
        <button
          type="button"
          className="primary"
          disabled={status === 'saving' || !draft.hcp_name}
          onClick={() => dispatch(saveInteraction(draft))}
        >
          {status === 'saving' ? 'Saving…' : draft.id ? 'Update Interaction' : 'Save Interaction'}
        </button>
      </div>
    </div>
  )
}
