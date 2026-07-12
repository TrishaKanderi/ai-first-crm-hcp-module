import { useEffect } from 'react'
import { useDispatch } from 'react-redux'
import { fetchInteractions } from '../store/interactionsSlice'
import InteractionForm from './InteractionForm'
import ChatPanel from './ChatPanel'
import './LogInteractionScreen.css'

export default function LogInteractionScreen() {
  const dispatch = useDispatch()

  useEffect(() => {
    dispatch(fetchInteractions())
  }, [dispatch])

  return (
    <div className="log-screen">
      <div className="panel form-side">
        <InteractionForm />
      </div>
      <div className="panel chat-side">
        <ChatPanel />
      </div>
    </div>
  )
}
