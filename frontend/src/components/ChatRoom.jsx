import React, { useState, useEffect, useRef } from 'react';
import { Send, User, Bot } from 'lucide-react';

export default function ChatRoom({ incidentId, userName }) {
    const [messages, setMessages] = useState([]);
    const [inputText, setInputText] = useState("");
    const [isConnected, setIsConnected] = useState(false);
    const ws = useRef(null);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        // Connect WebSocket
        ws.current = new WebSocket(`ws://127.0.0.1:8000/ws/chat/${incidentId}`);

        ws.current.onopen = () => {
            console.log("Connected to War-Room");
            setIsConnected(true);
        };

        ws.current.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setMessages((prev) => [...prev, data]);
        };

        ws.current.onclose = () => {
            console.log("Disconnected");
            setIsConnected(false);
        };

        return () => {
            ws.current.close();
        };
    }, [incidentId]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const sendMessage = () => {
        if (inputText.trim() && isConnected) {
            const payload = {
                sender: userName,
                message: inputText
            };
            ws.current.send(JSON.stringify(payload));
            setInputText("");
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') sendMessage();
    };

    return (
        <div className="flex flex-col h-screen bg-gray-100 max-w-md mx-auto border-x border-gray-300 shadow-xl">
            {/* Header */}
            <div className="bg-blue-900 text-white p-4 shadow-md flex justify-between items-center z-10">
                <div>
                    <h1 className="text-lg font-bold">🚨 AI War-Room</h1>
                    <p className="text-xs text-blue-200">Incident #{incidentId} | {isConnected ? "🟢 Online" : "🔴 Offline"}</p>
                </div>
                <div className="bg-red-600 px-2 py-1 rounded text-xs font-bold animate-pulse">
                    LEVEL 3
                </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg, index) => {
                    const isMe = msg.sender === userName;
                    const isSystem = msg.sender === "System";
                    
                    if (isSystem) {
                         return (
                            <div key={index} className="flex justify-center my-2">
                                <span className="bg-gray-200 text-gray-600 text-xs px-2 py-1 rounded-full">{msg.message}</span>
                            </div>
                        );
                    }

                    return (
                        <div key={index} className={`flex ${isMe ? "justify-end" : "justify-start"}`}>
                            {!isMe && (
                                <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center mr-2 text-white shrink-0">
                                    <User size={16} />
                                </div>
                            )}
                            <div className={`max-w-[70%] p-3 rounded-2xl shadow-sm text-sm ${
                                isMe 
                                    ? "bg-blue-600 text-white rounded-br-none" 
                                    : "bg-white text-gray-800 rounded-bl-none border border-gray-200"
                            }`}>
                                <p className="font-bold text-xs mb-1 opacity-70">{msg.sender}</p>
                                <p>{msg.message}</p>
                                <p className="text-[10px] opacity-50 text-right mt-1">
                                    {msg.timestamp?.split(' ')[1]?.slice(0,5)}
                                </p>
                            </div>
                        </div>
                    );
                })}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-3 bg-white border-t border-gray-200">
                <div className="flex items-center space-x-2">
                    <input 
                        type="text" 
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="메시지 입력..."
                        className="flex-1 border border-gray-300 rounded-full px-4 py-2 text-sm focus:outline-none focus:border-blue-500 bg-gray-50"
                    />
                    <button 
                        onClick={sendMessage}
                        disabled={!isConnected}
                        className="bg-blue-600 text-white p-2 rounded-full hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
                    >
                        <Send size={20} />
                    </button>
                </div>
            </div>
        </div>
    );
}
