import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Trash2, Sparkles } from 'lucide-react'
import clsx from 'clsx'
import { useMutation } from '@tanstack/react-query'
import { askChat } from '@/services/api'
import type { ChatMessage, ChatResponse } from '@/types'
import { Button } from '@/components/ui/Button'

const EXAMPLE_PROMPTS = [
  'What are the main legal risks for this project?',
  'How does the developer compare to others in Mumbai?',
  'What is the expected price appreciation in 3 years?',
  'Are there any NCLT proceedings against this developer?',
  'What RERA complaints are on record?',
]

export interface ChatInterfaceProps {
  projectId?: string
  projectName?: string
}

interface MessageBubble extends ChatMessage {
  id: string
  isStreaming?: boolean
}

export function ChatInterface({ projectId, projectName }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<MessageBubble[]>([])
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () =>
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })

  useEffect(() => { scrollToBottom() }, [messages])

  const { mutate: sendMessage, isPending } = useMutation<ChatResponse, Error, string>({
    mutationFn: (message: string) => {
      const history: ChatMessage[] = messages.map(({ role, content }) => ({ role, content }))
      return askChat(message, projectId, history)
    },
    onMutate: (message) => {
      const userMsg: MessageBubble = {
        id: crypto.randomUUID(),
        role: 'user',
        content: message,
      }
      const botMsg: MessageBubble = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        isStreaming: true,
      }
      setMessages((prev) => [...prev, userMsg, botMsg])
    },
    onSuccess: (data) => {
      setMessages((prev) => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last?.isStreaming) {
          updated[updated.length - 1] = {
            ...last,
            content: data.response,
            isStreaming: false,
          }
        }
        return updated
      })
    },
    onError: (err) => {
      setMessages((prev) => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last?.isStreaming) {
          updated[updated.length - 1] = {
            ...last,
            content: `Sorry, I encountered an error: ${err.message}`,
            isStreaming: false,
          }
        }
        return updated
      })
    },
  })

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || isPending) return
    setInput('')
    sendMessage(trimmed)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full min-h-[500px] bg-white rounded-2xl border border-slate-100 shadow-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-propiq-gradient flex items-center justify-center">
            <Sparkles size={14} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-propiq-navy">PropIQ AI</p>
            {projectName && (
              <p className="text-xs text-propiq-teal font-medium">
                Context: {projectName}
              </p>
            )}
          </div>
        </div>
        {messages.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setMessages([])}
            leftIcon={<Trash2 size={13} />}
            className="text-slate-400 hover:text-red-500"
          >
            Clear
          </Button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 ? (
          <EmptyState projectName={projectName} onPrompt={(p) => { setInput(p); inputRef.current?.focus() }} />
        ) : (
          messages.map((msg) => (
            <MessageRow key={msg.id} message={msg} />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-slate-100 bg-slate-50">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={projectId ? 'Ask about this project...' : 'Ask PropIQ AI anything about real estate...'}
            rows={1}
            className="flex-1 resize-none bg-white border border-slate-200 rounded-xl px-3 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-propiq-blue/30 focus:border-propiq-blue max-h-32 overflow-y-auto"
            style={{ minHeight: '42px' }}
            disabled={isPending}
            aria-label="Message input"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isPending}
            aria-label="Send message"
            className={clsx(
              'w-10 h-10 rounded-xl flex items-center justify-center transition-all shrink-0',
              input.trim() && !isPending
                ? 'bg-propiq-navy text-white hover:bg-navy-600 shadow-sm'
                : 'bg-slate-200 text-slate-400 cursor-not-allowed',
            )}
          >
            <Send size={16} />
          </button>
        </div>
        <p className="text-2xs text-slate-400 mt-1.5 text-center">
          PropIQ AI can make mistakes. Verify critical information before investing.
        </p>
      </div>
    </div>
  )
}

function MessageRow({ message }: { message: MessageBubble }) {
  const isUser = message.role === 'user'
  return (
    <div className={clsx('flex items-end gap-2', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div
        className={clsx(
          'w-7 h-7 rounded-full flex items-center justify-center shrink-0 mb-0.5',
          isUser ? 'bg-propiq-blue' : 'bg-propiq-gradient',
        )}
      >
        {isUser ? <User size={13} className="text-white" /> : <Bot size={13} className="text-white" />}
      </div>

      {/* Bubble */}
      <div
        className={clsx(
          'max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
          isUser
            ? 'bg-propiq-blue text-white rounded-br-sm'
            : 'bg-slate-100 text-slate-800 rounded-bl-sm',
        )}
      >
        {message.isStreaming ? (
          <TypingIndicator />
        ) : (
          <p className="whitespace-pre-wrap">{message.content}</p>
        )}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-2 h-2 rounded-full bg-slate-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  )
}

function EmptyState({
  projectName,
  onPrompt,
}: {
  projectName?: string
  onPrompt: (p: string) => void
}) {
  return (
    <div className="flex flex-col items-center py-8 px-4 text-center">
      <div className="w-14 h-14 rounded-2xl bg-propiq-gradient flex items-center justify-center mb-4">
        <Sparkles size={24} className="text-white" />
      </div>
      <h3 className="font-semibold text-propiq-navy mb-1">Ask PropIQ AI</h3>
      <p className="text-sm text-slate-500 mb-6 max-w-xs">
        {projectName
          ? `I have full context on ${projectName}. Ask me anything about it.`
          : 'Ask me anything about Indian real estate, RERA compliance, or developer track records.'}
      </p>
      <div className="flex flex-col gap-2 w-full max-w-sm">
        {EXAMPLE_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => onPrompt(p)}
            className="text-left text-sm bg-slate-50 hover:bg-navy-50 border border-slate-200 hover:border-propiq-blue/40 text-slate-600 hover:text-propiq-navy px-4 py-2.5 rounded-xl transition-all"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  )
}
