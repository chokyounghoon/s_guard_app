import React from 'react';
import ChatRoom from './components/ChatRoom';

function App() {
  // Hardcoded for demo
  const INCIDENT_ID = "1";
  const USER_NAME = "조경훈(Engineer)";

  return (
    <div className="min-h-screen bg-slate-800 flex justify-center items-center">
      {/* Simulate Mobile View on Desktop */}
      <ChatRoom incidentId={INCIDENT_ID} userName={USER_NAME} />
    </div>
  );
}

export default App;
