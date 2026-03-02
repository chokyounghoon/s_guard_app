import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Phone, Menu, Plus, Send, Home, MessageSquare, BarChart2, Settings, Info, AlertTriangle, ChevronDown, ChevronUp, Users, LogOut, FileText, UserPlus, Bot, Sparkles, Zap, X } from 'lucide-react';
import AIChatBubble from '../components/AIChatBubble';
import AIThinkingIndicator from '../components/AIThinkingIndicator';
import ServerStatusChart from '../components/chat/ServerStatusChart';

export default function ChatPage() {
  const navigate = useNavigate();
  const [isLogExpanded, setIsLogExpanded] = useState(true);
  const [showPhoneList, setShowPhoneList] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [showAIAssistant, setShowAIAssistant] = useState(false);
  const [aiMessages, setAiMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [isAiThinking, setIsAiThinking] = useState(false);

  const participants = [
    { name: '정도현 팀장', role: 'Team Leader', phone: '010-1234-5678' },
    { name: '시스템 어드민', role: 'Admin', phone: '010-9876-5432' },
    { name: '최광훈 담당', role: 'Developer', phone: '010-5555-5555' },
    { name: '이수민 매니저', role: 'Manager', phone: '010-1111-2222' },
    { name: '김철수 사원', role: 'Staff', phone: '010-3333-4444' },
    { name: '박영희 대리', role: 'Assistant', phone: '010-7777-8888' },
  ];

  // Main Chat State
  const [mainMessages, setMainMessages] = useState([]);
  const [mainInput, setMainInput] = useState('');
  const incidentId = 'INC-8823'; // Hardcoded for demo
  const currentUser = { name: '이수민 매니저', role: 'Manager' }; // Hardcoded current user

  // Load chat history on mount
  React.useEffect(() => {
    const fetchChatHistory = async () => {
      try {
        const res = await fetch(`http://localhost:8000/warroom/chat/${incidentId}`);
        if (res.ok) {
          const data = await res.json();
          const loadedMessages = data.messages.map(msg => ({
            id: msg.id,
            type: msg.type === 'me' || msg.sender === currentUser.name ? 'me' : 
                 (msg.type === 'system' ? 'system' : 'other'),
            sender: msg.sender,
            role: msg.role,
            initials: msg.sender ? msg.sender.substring(0, 2) : 'SY',
            color: 'bg-slate-700', // Simplify colors for now
            text: msg.text,
            time: new Date(msg.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
            icon: msg.type === 'system' ? Info : null
          }));
          
          if (loadedMessages.length === 0) {
            // Seed initial greeting if empty
            saveChatToDb({
              incident_id: incidentId,
              sender: '시스템',
              role: 'System',
              type: 'system',
              text: 'War-Room 채팅방이 생성되었습니다. 모든 대화 내용은 장애 해결 시 AI 학습에 사용됩니다.'
            });
          } else {
            setMainMessages(loadedMessages);
          }
        }
      } catch (err) {
        console.error("Failed to load chat history", err);
      }
    };
    fetchChatHistory();
  }, [incidentId]);

  const saveChatToDb = async (messageData) => {
    try {
      const res = await fetch('http://localhost:8000/warroom/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(messageData)
      });
      if (res.ok) {
        const saved = await res.json();
        const newMessage = {
          id: saved.id || Date.now(),
          type: messageData.type === 'me' ? 'me' : (messageData.type === 'system' ? 'system' : 'other'),
          sender: messageData.sender,
          role: messageData.role,
          initials: messageData.sender.substring(0, 2),
          color: messageData.type === 'system' ? 'bg-indigo-600' : 'bg-slate-700',
          text: messageData.text,
          time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
        };
        setMainMessages(prev => [...prev, newMessage]);
      }
    } catch (err) {
      console.error("Failed to save chat", err);
    }
  };

  const handleCall = (phoneNumber) => {
    window.location.href = `tel:${phoneNumber}`;
    setShowPhoneList(false);
  };

  // AI Assistant Logic
  const quickActions = [
    { id: 'status', label: '현재 서버 상태 알려줘', icon: BarChart2 },
    { id: 'error', label: '이 에러 원인 분석해줘', icon: AlertTriangle },
    { id: 'history', label: '유사 장애 이력 찾아줘', icon: FileText },
    { id: 'action', label: '조치 방법 추천해줘', icon: Zap }
  ];

  const handleAIMessage = async (message) => {
    if (!message.trim()) return;

    // Add user message
    const userMessage = {
      type: 'user',
      text: message,
      timestamp: new Date()
    };
    
    setAiMessages(prev => [...prev, userMessage]);
    setUserInput('');
    setIsAiThinking(true);

    try {
      const apiResponse = await fetch('http://localhost:8000/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: message })
      });
      
      if (!apiResponse.ok) {
        throw new Error(`API Error: ${apiResponse.status}`);
      }
      
      const data = await apiResponse.json();
      
      const aiMessage = {
        type: 'ai',
        text: data.response,
        logs: data.related_logs || [],
        timestamp: new Date()
      };

      setAiMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error("Failed to connect to AI backend:", error);
      const errorMessage = {
        type: 'ai',
        text: "현재 AI 에이전트 서비스 응답이 지연되고 있거나 연결할 수 없습니다. 서버 상태를 확인해주세요.",
        timestamp: new Date()
      };
      setAiMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsAiThinking(false);
    }
  };

  const handleQuickAction = (action) => {
    handleAIMessage(action.label);
  };

  const handleCopyMessage = (text) => {
    navigator.clipboard.writeText(text);
    alert('메시지가 클립보드에 복사되었습니다.');
  };

  const handleShareToTeam = (text) => {
    const shareText = `[AI Analysis Shared]\n\n${text}`;
    saveChatToDb({
      incident_id: incidentId,
      sender: currentUser.name,
      role: currentUser.role,
      type: 'me',
      text: shareText
    });
    setShowAIAssistant(false);
  };

  const handleMainSendMessage = () => {
    if (!mainInput.trim()) return;
    saveChatToDb({
      incident_id: incidentId,
      sender: currentUser.name,
      role: currentUser.role,
      type: 'me',
      text: mainInput
    });
    setMainInput('');
  };

  const handleResolveIncident = async () => {
    if (!confirm('이 장애 상황을 해결(Resolve) 처리하고 해당 대화 내용을 AI RAG Knowledge Base에 학습시키겠습니까?')) return;
    
    try {
      const res = await fetch(`http://localhost:8000/warroom/resolve/${incidentId}`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        alert(`성공: ${data.message} (${data.message_count_processed}개의 메시지 학습됨)`);
        saveChatToDb({
          incident_id: incidentId,
          sender: '시스템',
          role: 'System',
          type: 'system',
          text: `장애 처리가 완료되어 전체 대화 내용이 RAG AI Knowledge Base에 성공적으로 학습되었습니다!`
        });
      } else {
        alert('학습 중 오류가 발생했습니다.');
      }
    } catch (err) {
      console.error('Resolve failed', err);
      alert('서버와의 통신에 실패했습니다.');
    }
  };

  return (
    <div className="min-h-screen bg-[#0f1421] text-white font-sans flex flex-col pb-20 relative">
      {/* Header */}
      <header className="flex justify-between items-center p-4 sticky top-0 bg-[#0f1421]/90 backdrop-blur-md z-50 border-b border-white/5">
        <div className="flex items-center space-x-3">
          <button onClick={() => navigate(-1)} className="p-1 rounded-full hover:bg-white/10 transition-colors">
            <ArrowLeft className="w-6 h-6 text-white" />
          </button>
          <div className="flex flex-col">
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg">INC-8823</span>
              <span className="bg-red-500/20 text-red-500 text-[10px] font-bold px-2 py-0.5 rounded border border-red-500/30 uppercase tracking-tighter">
                CRITICAL
              </span>
            </div>
            <span className="text-slate-400 text-xs">장애 협업 채팅방 ({participants.length}명)</span>
          </div>
        </div>
        <div className="flex items-center space-x-4 relative">
          <button 
            onClick={() => { setShowPhoneList(!showPhoneList); setShowMenu(false); }}
            className={`p-1.5 rounded-full transition-colors ${showPhoneList ? 'bg-blue-500/20 text-blue-400' : 'hover:bg-white/10 text-slate-300'}`}
          >
            <Phone className="w-5 h-5" />
          </button>
          
          {/* Phone List Dropdown */}
          {showPhoneList && (
            <div className="absolute top-12 right-0 w-64 bg-[#1a1f2e] border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50">
                <div className="p-3 border-b border-white/5 bg-[#11141d]">
                    <span className="text-xs font-bold text-slate-300">통화 대상 선택</span>
                </div>
                <div className="max-h-60 overflow-y-auto">
                    {participants.map((person, index) => (
                        <div key={index} onClick={() => handleCall(person.phone)} className="flex items-center justify-between p-3 hover:bg-white/5 cursor-pointer transition-colors border-b border-white/5 last:border-0">
                            <div className="flex items-center space-x-3">
                                <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold">
                                    {person.name[0]}
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-sm text-white">{person.name}</span>
                                    <span className="text-[10px] text-slate-500">{person.role}</span>
                                </div>
                            </div>
                            <Phone className="w-4 h-4 text-green-500" />
                        </div>
                    ))}
                </div>
            </div>
          )}

          <button 
            onClick={() => { setShowMenu(!showMenu); setShowPhoneList(false); }}
            className={`p-1.5 rounded-full transition-colors ${showMenu ? 'bg-blue-500/20 text-blue-400' : 'hover:bg-white/10 text-slate-300'}`}
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Menu Dropdown */}
          {showMenu && (
            <div className="absolute top-12 right-0 w-48 bg-[#1a1f2e] border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50">
                <div 
                    onClick={() => { alert('사용자 초대 기능이 실행됩니다.'); setShowMenu(false); }}
                    className="flex items-center space-x-3 p-3 hover:bg-white/5 cursor-pointer transition-colors border-b border-white/5"
                >
                    <UserPlus className="w-4 h-4 text-blue-400" />
                    <span className="text-sm text-slate-200">초대하기</span>
                </div>
                <div 
                    onClick={() => { if(confirm('대화방을 나가시겠습니까?')) navigate('/dashboard'); }}
                    className="flex items-center space-x-3 p-3 hover:bg-red-500/10 cursor-pointer transition-colors"
                >
                    <LogOut className="w-4 h-4 text-red-400" />
                    <span className="text-sm text-red-400">나가기</span>
                </div>
            </div>
          )}
        </div>
      </header>

      {/* Persistent Error Log Banner (Collapsible) */}
      <div className="bg-red-950/10 border-b border-red-500/10 backdrop-blur-sm z-30 sticky top-[73px]">
        <div className="px-4 py-2">
            <div 
                onClick={() => setIsLogExpanded(!isLogExpanded)}
                className="flex items-center justify-between cursor-pointer group"
            >
                <div className="flex items-center space-x-2">
                    <AlertTriangle className="w-4 h-4 text-red-500 animate-pulse" />
                    <span className="text-xs font-bold text-red-400">🚨 현재 발생 중인 장애 (Ongoing Issue)</span>
                </div>
                <button className="p-1 rounded-full group-hover:bg-red-500/10 transition-colors">
                    {isLogExpanded ? <ChevronUp className="w-4 h-4 text-red-400" /> : <ChevronDown className="w-4 h-4 text-red-400" />}
                </button>
            </div>
            
            {isLogExpanded && (
                <div className="bg-[#0d0f14] rounded-lg border border-red-500/20 overflow-hidden mt-2 mb-1 animate-in slide-in-from-top-2 duration-200">
                    <div className="bg-red-900/10 px-3 py-1.5 border-b border-red-500/10 flex justify-between items-center">
                    <span className="text-[10px] text-red-300 font-mono">system_err.log</span>
                    <span className="text-[10px] text-red-400/70">Live Stream</span>
                    </div>
                    <div className="p-3 text-[11px] font-mono leading-relaxed">
                    <p className="text-red-400"><span className="font-bold">Error:</span> Connection timed out at port 8080.</p>
                    <p className="text-yellow-200/80 mt-1"><span className="font-bold text-yellow-500">Caused by:</span> java.net.ConnectException: Connection refused</p>
                    </div>
                </div>
            )}
        </div>
      </div>

      {/* Chat Area */}
      <main className="flex-1 p-4 space-y-6 overflow-y-auto pb-40">
        {/* Date Divider */}
        <div className="flex justify-center my-4">
          <div className="bg-slate-800/40 text-slate-400 text-[11px] px-4 py-1 rounded-full">
            2023년 10월 25일 수요일
          </div>
        </div>

        {mainMessages.map((msg) => (
          <div key={msg.id}>
            {msg.type === 'other' && (
              <div className="flex items-start space-x-3 mb-4">
                <div className={`w-10 h-10 rounded-xl ${msg.color} flex items-center justify-center font-bold text-sm shrink-0`}>
                  {msg.initials}
                </div>
                <div className="flex flex-col space-y-1">
                  <span className="text-xs text-slate-400 font-medium">{msg.sender}</span>
                  <div className="flex items-end space-x-2">
                    <div className="bg-slate-800/80 rounded-2xl rounded-tl-none px-4 py-2.5 max-w-[280px] text-[15px] leading-relaxed whitespace-pre-wrap">
                      {msg.text}
                    </div>
                    <span className="text-[10px] text-slate-500 pb-1">{msg.time}</span>
                  </div>
                </div>
              </div>
            )}

            {msg.type === 'me' && (
              <div className="flex flex-col items-end space-y-1 mb-4">
                <div className="flex items-end space-x-2">
                  <span className="text-[10px] text-slate-500 pb-1">{msg.time}</span>
                  <div className="bg-blue-600 rounded-2xl rounded-tr-none px-4 py-3 max-w-[280px] text-[15px] leading-relaxed shadow-lg shadow-blue-900/20 whitespace-pre-wrap">
                    {msg.text}
                  </div>
                </div>
              </div>
            )}

            {msg.type === 'system' && (
              <div className="flex justify-center mt-8 mb-8">
                <div className="bg-slate-800/30 border border-white/5 rounded-xl px-4 py-2.5 flex items-center space-x-3 max-w-[320px]">
                  <div className="p-1.5 bg-blue-500/20 rounded-full">
                     <msg.icon className="w-4 h-4 text-blue-400" />
                  </div>
                  <p className="text-[13px] text-slate-300" dangerouslySetInnerHTML={{ __html: msg.text }} />
                </div>
              </div>
            )}
          </div>
        ))}
      </main>
    
      {/* AI Assistant Panel */}
      {showAIAssistant && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" onClick={() => setShowAIAssistant(false)}>
          <div 
            className="absolute right-0 top-0 h-full w-full max-w-md bg-[#0f1421] border-l border-white/10 shadow-2xl flex flex-col animate-in slide-in-from-right duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            {/* AI Panel Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/10 bg-gradient-to-r from-purple-900/20 to-blue-900/20">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center shadow-lg">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-white">AI Assistant</h3>
                  <p className="text-[10px] text-slate-400">S-Autopilot 실시간 분석</p>
                </div>
              </div>
              <button
                onClick={() => setShowAIAssistant(false)}
                className="p-2 hover:bg-white/10 rounded-full transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            {/* Quick Actions */}
            {aiMessages.length === 0 && (
              <div className="p-4 space-y-3 border-b border-white/5">
                <p className="text-xs text-slate-400 mb-2">💡 빠른 질문</p>
                <div className="grid grid-cols-2 gap-2">
                  {quickActions.map((action) => (
                    <button
                      key={action.id}
                      onClick={() => handleQuickAction(action)}
                      className="flex items-center space-x-2 p-3 bg-gradient-to-br from-slate-800/60 to-slate-900/60 hover:from-purple-900/30 hover:to-blue-900/30 border border-white/5 hover:border-purple-500/30 rounded-xl text-left transition-all group"
                    >
                      <action.icon className="w-4 h-4 text-purple-400 group-hover:text-purple-300 flex-shrink-0" />
                      <span className="text-[11px] text-slate-300 leading-tight">{action.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* AI Chat Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              {aiMessages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center space-y-3">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-600/20 to-blue-600/20 flex items-center justify-center border border-purple-500/20">
                    <Bot className="w-8 h-8 text-purple-400" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white mb-1">AI와 대화를 시작하세요</h4>
                    <p className="text-xs text-slate-400 leading-relaxed max-w-xs">
                      서버 상태, 에러 원인, 조치 방법 등<br/>무엇이든 물어보세요!
                    </p>
                  </div>
                </div>
              )}

              {aiMessages.map((msg, index) => (
                <div key={index}>
                  {msg.type === 'user' ? (
                    <div className="flex flex-col items-end space-y-1">
                      <div className="bg-blue-600 rounded-2xl rounded-tr-none px-4 py-3 max-w-[85%] text-sm leading-relaxed shadow-lg shadow-blue-900/20">
                        {msg.text}
                      </div>
                      <span className="text-[10px] text-slate-500">
                        {msg.timestamp.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  ) : (
                    <>
                      <AIChatBubble 
                        message={msg}
                        onCopy={handleCopyMessage}
                        onShare={handleShareToTeam}
                      />
                      {msg.metrics && (
                        <div className="ml-10 max-w-[85%] mt-2 animate-fade-in-up">
                            <ServerStatusChart />
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}

              {isAiThinking && <AIThinkingIndicator />}
            </div>

            {/* AI Input Area */}
            <div className="p-3 border-t border-white/10 bg-[#0a0d14]">
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAIMessage(userInput)}
                  placeholder="AI에게 질문하세요..."
                  className="flex-1 bg-slate-800/60 rounded-full py-2.5 px-4 text-sm border border-white/5 focus:outline-none focus:border-purple-500/50 transition-all placeholder:text-slate-500"
                />
                <button
                  onClick={() => handleAIMessage(userInput)}
                  disabled={!userInput.trim()}
                  className="p-2.5 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white shadow-lg shadow-purple-900/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* New Analysis Action Bar */}
      <div className="px-4 pb-2 bg-[#0f1421]">
        <button 
            onClick={handleResolveIncident}
            className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-emerald-900/30 flex items-center justify-center space-x-2 transition-all active:scale-[0.98]"
        >
            <Settings className="w-5 h-5 animate-spin-slow" />
            <span>장애 해결(Resolve) 및 AI에 학습시키기</span>
        </button>
      </div>

      {/* Input Area */}
      <div className="p-3 bg-[#0f1421] border-t border-white/5 flex items-center space-x-3 mb-[70px]">
        <button className="p-2.5 rounded-full bg-slate-800/60 hover:bg-slate-700 transition-colors">
          <Plus className="w-6 h-6 text-slate-400" />
        </button>
        <div className="flex-1 relative">
           <input 
             type="text" 
             value={mainInput}
             onChange={(e) => setMainInput(e.target.value)}
             onKeyPress={(e) => e.key === 'Enter' && handleMainSendMessage()}
             placeholder="메시지를 입력하세요..." 
             className="w-full bg-slate-800/60 rounded-full py-2.5 px-5 text-[15px] border border-white/5 focus:outline-none focus:border-blue-500/50 transition-all placeholder:text-slate-500"
           />
           <button 
             onClick={handleMainSendMessage}
             disabled={!mainInput.trim()}
             className="absolute right-1 top-1 p-1.5 rounded-full bg-blue-600 text-white shadow-lg shadow-blue-900/40 disabled:opacity-50 disabled:cursor-not-allowed"
           >
              <Send className="w-5 h-5 fill-current" />
           </button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="fixed bottom-0 left-0 w-full bg-[#0f1421] border-t border-white/5 px-6 py-3 flex justify-between items-center z-50 pb-safe">
        <div className="flex flex-col items-center space-y-1 text-slate-500 hover:text-white transition-colors cursor-pointer" onClick={() => navigate('/dashboard')}>
            <Home className="w-6 h-6" />
            <span className="text-[10px] font-medium">홈</span>
        </div>
        <div className="flex flex-col items-center space-y-1 text-blue-500 relative cursor-pointer" onClick={() => navigate('/chat')}>
            <div className="relative">
                <MessageSquare className="w-6 h-6" />
                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-[#0f1421]"></span>
            </div>
            <span className="text-[10px] font-medium">War-Room</span>
        </div>

        <div className="flex flex-col items-center space-y-1 text-slate-500 hover:text-white transition-colors cursor-pointer">
            <BarChart2 className="w-6 h-6" />
            <span className="text-[10px] font-medium">통계</span>
        </div>
        
        {/* AI Assistant Nav Button */}
        <div 
          className={`flex flex-col items-center space-y-1 transition-colors cursor-pointer ${
            showAIAssistant ? 'text-purple-400' : 'text-slate-500 hover:text-purple-400'
          }`}
          onClick={() => setShowAIAssistant(!showAIAssistant)}
        >
            <div className="relative">
              <Bot className="w-6 h-6" />
              {!showAIAssistant && (
                <span className="absolute -top-1 -right-1 w-2 h-2 bg-purple-500 rounded-full border-2 border-[#0f1421] animate-pulse"></span>
              )}
            </div>
            <span className="text-[10px] font-medium">AI</span>
        </div>
        
        <div className="flex flex-col items-center space-y-1 text-slate-500 hover:text-white transition-colors cursor-pointer">
            <Settings className="w-6 h-6" />
            <span className="text-[10px] font-medium">설정</span>
        </div>
      </nav>
    </div>
  );
}
