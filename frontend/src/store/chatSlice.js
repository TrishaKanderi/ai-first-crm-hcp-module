import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { sendChatMessage } from '../api'
import { setActiveInteraction } from './interactionsSlice'

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async ({ message, activeInteractionId }, { dispatch }) => {
    const res = await sendChatMessage(message, activeInteractionId)
    if (res.data.interaction) {
      dispatch(setActiveInteraction(res.data.interaction))
    }
    return res.data
  }
)

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    messages: [
      {
        role: 'assistant',
        text:
          'Log interaction details here (e.g., "Met Dr. Smith, discussed Prodo-X efficacy, positive sentiment, shared brochure") or ask for help.',
      },
    ],
    status: 'idle',
  },
  reducers: {
    addUserMessage(state, action) {
      state.messages.push({ role: 'user', text: action.payload })
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state) => {
        state.status = 'thinking'
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.status = 'idle'
        state.messages.push({
          role: 'assistant',
          text: action.payload.reply,
          toolUsed: action.payload.tool_used,
        })
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.status = 'idle'
        state.messages.push({
          role: 'assistant',
          text: `Something went wrong reaching the assistant: ${action.error.message}`,
          isError: true,
        })
      })
  },
})

export const { addUserMessage } = chatSlice.actions
export default chatSlice.reducer
