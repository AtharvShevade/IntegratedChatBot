/**
 * SupportReport.jsx — "Report an issue" UI.
 *
 *   SupportReportOffer  the bubble shown after a 👎 rating: Report an issue / No thanks
 *   SupportReportForm   the form itself (category, description, opt-in Q&A); also opened
 *                       from the persistent link next to the composer
 *
 * The form keeps all of its state locally: nothing about a report (draft text,
 * opt-in question/answer, outcome) is written into the conversation messages,
 * so nothing is saved to the persisted chat history.
 */
import { createContext, useContext, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { useT } from '../i18n.js'
import { submitSupportRequest } from '../services/api.js'
import {
  CATEGORIES, DESCRIPTION_MAX, createSupportReport, descriptionLength, infoForCode, validateDescription,
} from '../support/supportReport.js'

/**
 * What the form needs from the app, provided once by App so it does not have to
 * be threaded through ChatWindow/MessageBubble: the session token to forward
 * (as /chat does), a getter for the CURRENT messages (read only on opt-in), and
 * restoreMenu: the next-action menu is hidden while the report offer/form is open and
 * brought back when the user declines or closes it.
 */
export const SupportReportContext = createContext({ getMessages: () => [], aspSession: '', restoreMenu: () => {} })

export function SupportReportForm({ defaultCategory = 'other', onClose, submit = submitSupportRequest, controller }) {
  const t = useT()
  const { getMessages, aspSession } = useContext(SupportReportContext)
  const [category, setCategory] = useState(defaultCategory)
  const [description, setDescription] = useState('')
  const [includeQa, setIncludeQa] = useState(false)
  const [touched, setTouched] = useState(false)
  // One controller per report: it owns the reference id (reused by retries) and the in-flight guard.
  const ctrlRef = useRef(controller || null)
  if (ctrlRef.current === null) ctrlRef.current = createSupportReport({ submit })
  const ctrl = ctrlRef.current
  const { status, result } = useSyncExternalStore(ctrl.subscribe, ctrl.getState, ctrl.getState)

  // Bring the whole form (and later its result) into view; the chat does not scroll by itself
  // when this local state changes, so the form used to open below the fold.
  const rootRef = useRef(null)
  useEffect(() => {
    rootRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' })
  }, [status])

  const problemKey = validateDescription(description)
  const showProblem = problemKey && (touched || problemKey === 'support.report.err.tooLong')
  const sending = status === 'sending'
  const info = result ? infoForCode(result.code) : null

  const handleSubmit = (e) => {
    e?.preventDefault?.()
    setTouched(true)
    // The question/answer are read inside the controller, and only when the box is ticked.
    ctrl.submit({ description, category, includeQa, lang: t.lang, aspSession, getMessages })
  }

  if (status === 'done' && result) {
    return (
      <div className="support-report" role="status" ref={rootRef}>
        <p className="support-report-msg support-report-success">{t(info.key)}</p>
        {result.referenceId && (
          <p className="support-report-ref">{t('support.report.reference')}: <bdi>{result.referenceId}</bdi></p>
        )}
        <div className="support-report-actions">
          <button type="button" className="support-report-btn" onClick={onClose}>{t('common.close')}</button>
        </div>
      </div>
    )
  }

  const count = descriptionLength(description)
  return (
    <form className="support-report" ref={rootRef} onSubmit={handleSubmit} noValidate aria-label={t('support.report.title')}>
      <p className="support-report-title">{t('support.report.title')}</p>

      <label className="support-report-label" htmlFor="support-report-category">{t('support.report.category')}</label>
      <select
        id="support-report-category"
        className="support-report-field"
        value={category}
        onChange={(e) => setCategory(e.target.value)}
        disabled={sending}
      >
        {CATEGORIES.map((c) => <option key={c} value={c}>{t(`support.report.cat.${c}`)}</option>)}
      </select>

      <label className="support-report-label" htmlFor="support-report-description">{t('support.report.description')}</label>
      <textarea
        id="support-report-description"
        className="support-report-field support-report-text"
        rows={4}
        value={description}
        placeholder={t('support.report.placeholder')}
        onChange={(e) => setDescription(e.target.value)}
        onBlur={() => setTouched(true)}
        disabled={sending}
        aria-invalid={showProblem ? 'true' : 'false'}
        aria-describedby="support-report-count support-report-problem"
      />
      <div className="support-report-meta">
        <span id="support-report-problem" className="support-report-problem" role={showProblem ? 'alert' : undefined}>
          {showProblem ? t(problemKey) : ''}
        </span>
        <span id="support-report-count" className={`support-report-count${count > DESCRIPTION_MAX ? ' over' : ''}`} dir="ltr">
          {count} / {DESCRIPTION_MAX}
        </span>
      </div>

      <label className="support-report-check">
        <input type="checkbox" checked={includeQa} onChange={(e) => setIncludeQa(e.target.checked)} disabled={sending} />
        <span>{t('support.report.includeQa')}</span>
      </label>
      <p className="support-report-hint">{t('support.report.includeQaHint')}</p>

      {status === 'failed' && info && (
        <p className={`support-report-msg support-report-${info.kind}`} role="alert">{t(info.key)}</p>
      )}
      {sending && <p className="support-report-msg" role="status">{t('support.report.sending')}</p>}

      <div className="support-report-actions">
        <button type="button" className="support-report-btn" onClick={onClose} disabled={sending}>{t('common.cancel')}</button>
        <button type="submit" className="support-report-btn support-report-primary" disabled={sending || count > DESCRIPTION_MAX}>
          {sending ? t('support.report.sending') : status === 'failed' && info?.kind === 'retry' ? t('support.report.retry') : t('common.submit')}
        </button>
      </div>
    </form>
  )
}

/** Shown after a negative rating: the apology, then Report an issue / No thanks. */
export function SupportReportOffer() {
  const t = useT()
  const { restoreMenu } = useContext(SupportReportContext)
  const [step, setStep] = useState('offer')              // offer | form | declined
  // No thanks, Cancel and Close all end the offer, and the next-action menu comes back.
  const finish = () => { setStep('declined'); restoreMenu?.() }
  return (
    <div className="bubble-row assistant">
      <div className="avatar assistant-avatar">AI</div>
      <div className="bubble assistant-bubble support-contact-bubble">
        <p className="support-sorry">{t('support.sorry')}</p>
        {step === 'offer' && (
          <div className="support-report-actions support-report-offer">
            <button type="button" className="support-report-btn support-report-primary" onClick={() => setStep('form')}>
              {t('support.report.open')}
            </button>
            <button type="button" className="support-report-btn" onClick={finish}>
              {t('support.report.decline')}
            </button>
          </div>
        )}
        {step === 'form' && (
          <SupportReportForm
            defaultCategory="incorrect_answer"
            onClose={finish}
          />
        )}
      </div>
    </div>
  )
}
