import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble.jsx'

export default function ChatWindow({ messages, isLoading, onFollowUp, onSuggestion, onGuidedAction, onCompare, onFeedback, onExplainCategory, allowedActions }) {
  const bottomRef = useRef(null)

  // Auto-scroll to the latest message whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="chat-window">
      {messages.map((msg, idx) => (
        <MessageBubble
          key={idx}
          role={msg.role}
          text={msg.text}
          data={msg.data}
          options={msg.options}
          resultType={msg.resultType}
          feedbackQuery={msg.query}
          feedbackIntent={msg.intent}
          sqlData={msg.sqlData}
          dbQaData={msg.dbQaData}
          varianceData={msg.varianceData}
          labelA={msg.labelA}
          labelB={msg.labelB}
          llmSummary={msg.llmSummary}
          instancesData={msg.instancesData}
          downloadUrl={msg.downloadUrl}
          downloadLabel={msg.downloadLabel}
          statusNote={msg.statusNote}
          errorDetails={msg.errorDetails}
          jobId={msg.jobId}
          batchCategory={msg.batchCategory}
          batchErrorFilePath={msg.batchErrorFilePath}
          batchFormId={msg.batchFormId}
          batchReportName={msg.batchReportName}

          onFollowUp={onFollowUp}
          onSuggestion={onSuggestion}
          onGuidedAction={onGuidedAction}
          onCompare={onCompare}
          onFeedback={onFeedback}
          onExplainCategory={(cat, errorFilePath, formId, reportName, offset) => onExplainCategory?.(cat, errorFilePath, formId, reportName, offset)}
          allowedActions={allowedActions}
        />
      ))}

      {/* Typing indicator shown while waiting for the backend */}
      {isLoading && (
        <div className="bubble-row assistant">
          <div className="avatar assistant-avatar">AI</div>
          <div className="bubble assistant-bubble typing-indicator">
            <span /><span /><span />
          </div>
        </div>
      )}

      {/* Invisible anchor used for auto-scroll */}
      <div ref={bottomRef} />
    </div>
  )
}