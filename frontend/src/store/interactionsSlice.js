import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { createInteraction, updateInteraction, listInteractions } from '../api'

const emptyDraft = {
  hcp_name: '',
  interaction_type: 'Meeting',
  interaction_date: '',
  interaction_time: '',
  attendees: [],
  topics_discussed: '',
  materials_shared: [],
  samples_distributed: [],
  sentiment: 'Neutral',
  outcomes: '',
  follow_up_actions: [],
  compliance_flags: [],
}

export const saveInteraction = createAsyncThunk(
  'interactions/save',
  async (draft) => {
    if (draft.id) {
      const res = await updateInteraction(draft.id, draft)
      return res.data
    }
    const res = await createInteraction(draft)
    return res.data
  }
)

export const fetchInteractions = createAsyncThunk('interactions/fetchAll', async (hcpName) => {
  const res = await listInteractions(hcpName)
  return res.data
})

const interactionsSlice = createSlice({
  name: 'interactions',
  initialState: {
    draft: emptyDraft,
    list: [],
    status: 'idle',
    error: null,
  },
  reducers: {
    updateDraftField(state, action) {
      const { field, value } = action.payload
      state.draft[field] = value
    },
    setActiveInteraction(state, action) {
      state.draft = { ...emptyDraft, ...action.payload }
    },
    resetDraft(state) {
      state.draft = emptyDraft
    },
    addListItem(state, action) {
      // field is one of materials_shared / samples_distributed / attendees
      const { field, value } = action.payload
      if (!value) return
      state.draft[field] = [...(state.draft[field] || []), value]
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(saveInteraction.pending, (state) => {
        state.status = 'saving'
      })
      .addCase(saveInteraction.fulfilled, (state, action) => {
        state.status = 'idle'
        state.draft = action.payload
        const idx = state.list.findIndex((i) => i.id === action.payload.id)
        if (idx >= 0) state.list[idx] = action.payload
        else state.list.unshift(action.payload)
      })
      .addCase(saveInteraction.rejected, (state, action) => {
        state.status = 'error'
        state.error = action.error.message
      })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.list = action.payload
      })
  },
})

export const { updateDraftField, setActiveInteraction, resetDraft, addListItem } = interactionsSlice.actions
export default interactionsSlice.reducer
