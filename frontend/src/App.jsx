import LogInteractionScreen from './components/LogInteractionScreen'

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="dot" />
          AI-First CRM · HCP Module
        </div>
        <div className="subtitle">Log Interaction</div>
      </header>
      <main className="screen-body">
        <LogInteractionScreen />
      </main>
    </div>
  )
}
