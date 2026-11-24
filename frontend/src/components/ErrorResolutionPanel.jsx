import { useRef, useState } from 'react'
import ChatWindow from './ChatWindow.jsx'
import { uploadErrorFile, setErrorUploadForm, explainUploadedError } from '../services/api.js'
import { useT } from '../i18n.js'
import './ErrorResolutionPanel.css'

// Failed-status code the summary card needs so MessageBubble shows the per-category "Explain" buttons (see FAILED_STATUS_CODES there).
const FAILED_STATUS = 8
const ACCEPT = '.html,.htm,.xml'

/**
 * "Error Resolution" tab: upload the error file a failed generation produced, get the same explanation cards as check-status.
 *
 * The results are ordinary chat messages rendered by the same MessageBubble / ChatWindow the chat uses, so a card here is the
 * very card the chat shows (and an "Explain next errors" button pages exactly as it does there). Only the plumbing differs:
 * the file is uploaded once (upload_id), and every batch is requested by that id, never by a path.
 */
export default function ErrorResolutionPanel({ lang, loginId, tenantId, domain, jwtRef }) {
  const t = useT()
  const fileRef = useRef(null)
  const [upload, setUpload] = useState(null)        // the last upload response
  const [messages, setMessages] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [formInput, setFormInput] = useState('')
  const [dragOver, setDragOver] = useState(false)

  const ident = () => ({ loginId, tenantId, domain, jwt: jwtRef?.current || null })
  const fail = (err) => setError(err?.message || t(err?.i18nKey || 'errorResolution.uploadFailed'))

  // The summary card: the existing error-summary panel (counts + Explain buttons) inside a normal assistant message.
  const summaryMessage = (u) => {
    const counts = u.error_category_counts || {}
    const any = ['formula_error', 'xbrl_schema', 'dimensional'].some((c) => counts[c] > 0) || counts.formula_total > 0
    return {
      role: 'assistant',
      resultType: 'final',
      text: any
        ? `${t('errorResolution.summary')} ${u.filename}${u.form_id ? ` · ${t('errorResolution.matched')} ${u.form_id}${u.report_name ? ` (${u.report_name})` : ''}` : ''}\n${t('errorResolution.pick')}`
        : t('errorResolution.noErrors'),
      reportName: u.report_name || '',
      data: { status_code: FAILED_STATUS, error_category_counts: counts, form_id: u.form_id, report_name: u.report_name, is_4000_series: !!u.is_4000_series },
    }
  }

  const show = (u) => {
    setUpload(u)
    setMessages(u.needs_form ? [] : [summaryMessage(u)])
  }

  const send = async (file) => {
    if (!file || busy) return
    setBusy(true); setError(''); setUpload(null); setMessages([])
    try {
      show(await uploadErrorFile(file, ident()))
    } catch (err) {
      fail(err)
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const chooseForm = async (formId) => {
    const id = (formId || '').trim()
    if (!id || !upload || busy) return
    setBusy(true); setError('')
    try {
      show(await setErrorUploadForm(upload.upload_id, id, ident()))
    } catch (err) {
      fail(err)
    } finally {
      setBusy(false)
    }
  }

  // Same signature the chat's cards call: (category, filename, formId, reportName, offset). The filename/formId are ignored on
  // purpose: the server already holds the file under upload_id.
  const explain = async (category, _file, _form, _report, offset = 0) => {
    if (!upload || busy) return
    setBusy(true); setError('')
    try {
      const result = await explainUploadedError(upload.upload_id, category, { offset, lang, ...ident() })
      setMessages((prev) => [...prev, {
        role: result.result_type === 'error' ? 'error' : 'assistant',
        text: result.response_text || '',
        reportName: result.report_name || '',
        data: result.data || null,
        options: result.options || [],
        resultType: result.result_type || '',
        errorDetails: result.error_details || [],
        batchCategory: category,
        batchErrorFilePath: upload.filename,
        batchFormId: upload.form_id,
        batchReportName: upload.report_name,
      }])
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'error', text: err?.message || t(err?.i18nKey || 'errors.explanationFailed') }])
    } finally {
      setBusy(false)
    }
  }

  const onDrop = (e) => {
    e.preventDefault(); setDragOver(false)
    send(e.dataTransfer?.files?.[0])
  }

  return (
    <div className="er-panel">
      <div className="er-top">
        <div
          className={`er-drop${dragOver ? ' er-drop-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
        >
          <div className="er-title">{t('errorResolution.title')}</div>
          <p className="er-hint">{t('errorResolution.hint')}</p>
          <input ref={fileRef} type="file" accept={ACCEPT} hidden onChange={(e) => send(e.target.files?.[0])} />
          <button type="button" className="er-btn" disabled={busy} onClick={() => fileRef.current?.click()}>
            {upload ? t('errorResolution.another') : t('errorResolution.choose')}
          </button>
          <span className="er-drop-text">{t('errorResolution.dropHere')}</span>
          {busy && !upload && <div className="er-status" role="status">{t('errorResolution.analysing')}</div>}
          {error && <div className="er-error" role="alert">{error}</div>}
        </div>

        {upload?.needs_form && (
          <div className="er-pick">
            <div className="er-title">{t('errorResolution.whichReturn')}</div>
            <p className="er-hint">{t('errorResolution.whichReturnHint')}</p>
            {upload.candidates?.length > 0 && (
              <div className="er-chips">
                {upload.candidates.map((c) => (
                  <button key={c.form_id} type="button" className="suggestion-chip" disabled={busy} onClick={() => chooseForm(c.form_id)}>
                    {c.form_id}
                  </button>
                ))}
              </div>
            )}
            <form className="er-form" onSubmit={(e) => { e.preventDefault(); chooseForm(formInput) }}>
              <input
                className="er-input" inputMode="numeric" pattern="[0-9]*" maxLength={6}
                value={formInput} onChange={(e) => setFormInput(e.target.value.replace(/\D/g, ''))}
                placeholder={t('errorResolution.returnId')} aria-label={t('errorResolution.returnId')}
              />
              <button type="submit" className="er-btn" disabled={busy || !formInput}>{t('errorResolution.continue')}</button>
            </form>
          </div>
        )}
      </div>

      <div className="er-results">
        <ChatWindow
          messages={messages}
          isLoading={busy && !!upload}
          onExplainCategory={explain}
          lang={lang}
          loginId={loginId || null}
          tenantId={tenantId || null}
          domain={domain || null}
          jwtRef={jwtRef}
        />
      </div>
    </div>
  )
}
