import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { API_URL } from './config'
import { useNavigate } from 'react-router-dom'

interface Message {
    id: number;
    text: string;
    sender: 'user' | 'nila';
    time: string;
}

export default function Chat() {
    const [messages, setMessages] = useState<Message[]>([])
    const [inputText, setInputText] = useState("")
    const [isTyping, setIsTyping] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const navigate = useNavigate()

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages, isTyping])

    // Fetch History on Load
    useEffect(() => {
        const fetchHistory = async () => {
            const token = localStorage.getItem('token');
            if (!token) {
                navigate('/login');
                return;
            }

            try {
                const response = await axios.get(`${API_URL}/history`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                setMessages(response.data);
            } catch (error) {
                console.error("Failed to load history", error);
                if (axios.isAxiosError(error) && error.response?.status === 401) {
                    localStorage.removeItem('token');
                    navigate('/login');
                }
            }
        };
        fetchHistory();
    }, [navigate]);

    const handleSend = async () => {
        const token = localStorage.getItem('token');
        if (!token) { navigate('/login'); return; }
        if (!inputText.trim()) return

        const userMsg: Message = {
            id: Date.now(),
            text: inputText,
            sender: 'user',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }

        setMessages(prev => [...prev, userMsg])
        setInputText("")
        setIsTyping(true)

        try {
            const response = await axios.post(`${API_URL}/chat`, {
                message: userMsg.text
            }, {
                headers: { Authorization: `Bearer ${token}` }
            })

            const replyBubbles: string[] = response.data.messages
            displayBubblesWithDelay(replyBubbles, 0)

        } catch (error) {
            console.error("Error sending message:", error)
            setIsTyping(false)
            if (axios.isAxiosError(error) && error.response?.status === 401) {
                navigate('/login');
            }
        }
    }

    const displayBubblesWithDelay = (bubbles: string[], index: number) => {
        if (index >= bubbles.length) {
            setIsTyping(false)
            return
        }

        const baseDelay = 800
        const randomVar = Math.random() * 500
        const delay = index === 0 ? baseDelay + randomVar : (baseDelay / 2) + randomVar

        setTimeout(() => {
            const newMsg: Message = {
                id: Date.now() + index,
                text: bubbles[index],
                sender: 'nila',
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            }

            setMessages(prev => [...prev, newMsg])

            if (index < bubbles.length - 1) {
                setIsTyping(true)
                displayBubblesWithDelay(bubbles, index + 1)
            } else {
                setIsTyping(false)
            }
        }, delay)
    }

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/login');
    }

    return (
        <div className="flex justify-center items-center bg-warm-bg font-sans" style={{ height: '100dvh' }}>
            <div className="w-full max-w-[900px] flex flex-col bg-warm-bg overflow-hidden shadow-2xl md:rounded-3xl md:border-4 md:border-white/50" style={{ height: '100dvh', maxHeight: '100dvh' }}>

                {/* Sticky Header */}
                <header className="flex-shrink-0 mx-5 mt-5 mb-2 h-[70px] bg-white rounded-full flex items-center px-5 shadow-sm z-50">
                    <div className="w-[45px] h-[45px] rounded-full overflow-hidden shadow-sm mr-4 border border-gray-100">
                        <img src="https://api.dicebear.com/9.x/micah/svg?seed=Nila" alt="Avatar" className="w-full h-full object-cover" />
                    </div>
                    <div className="flex-1">
                        <h2 className="m-0 text-base font-semibold text-nila-text">Nila</h2>
                        <p className="m-0 text-xs text-nila-subtext">{isTyping ? "typing..." : "Online"}</p>
                    </div>
                    <div className="text-sage-accent cursor-pointer hover:text-red-500 transition-colors" onClick={handleLogout} title="Logout">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
                    </div>
                </header>

                {/* Chat Area */}
                <div className="flex-1 px-5 py-3 overflow-y-auto flex flex-col gap-3 scrollbar-hide bg-warm-bg min-h-0">
                    {messages.map((msg) => (
                        <div
                            key={msg.id}
                            className={`relative max-w-[75%] px-5 py-3 rounded-3xl shadow-sm text-[15px] leading-relaxed break-words flex flex-wrap items-end gap-2 animate-popIn transition-all duration-300
                ${msg.sender === 'user'
                                    ? 'self-end bg-wheat-bubble rounded-br-md text-nila-text'
                                    : 'self-start bg-white-bubble rounded-bl-md text-nila-text'}`}
                        >
                            <div className="text-nila-text">{msg.text}</div>
                            <span className="text-[10px] text-nila-subtext opacity-70 whitespace-nowrap mb-[2px] ml-auto">{msg.time}</span>
                        </div>
                    ))}

                    {isTyping && (
                        <div className="self-start bg-white-bubble px-5 py-3 rounded-3xl rounded-bl-md flex items-center gap-[5px] shadow-sm mb-2 w-fit">
                            <div className="w-[6px] h-[6px] bg-gray-400 rounded-full animate-bounce [animation-delay:-0.32s]"></div>
                            <div className="w-[6px] h-[6px] bg-gray-400 rounded-full animate-bounce [animation-delay:-0.16s]"></div>
                            <div className="w-[6px] h-[6px] bg-gray-400 rounded-full animate-bounce"></div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Sticky Input Area */}
                <div className="flex-shrink-0 p-5 flex items-center gap-3 z-50 bg-gradient-to-t from-warm-bg via-warm-bg to-transparent pb-6">
                    <input
                        type="text"
                        className="flex-1 border-none px-6 py-4 rounded-full text-[15px] outline-none bg-white h-[55px] shadow-sm text-nila-text placeholder-gray-300 focus:shadow-md transition-shadow will-change-transform"
                        placeholder="Message..."
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    />
                    <button
                        className="bg-white border-none text-sage-accent w-[55px] h-[55px] rounded-full flex items-center justify-center cursor-pointer shadow-sm hover:-translate-y-0.5 hover:shadow-md hover:text-[#a09070] disabled:text-gray-200 disabled:cursor-default disabled:transform-none disabled:shadow-sm transition-all duration-200"
                        onClick={handleSend}
                        disabled={!inputText.trim()}
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                    </button>
                </div>
            </div>
        </div>
    )
}
