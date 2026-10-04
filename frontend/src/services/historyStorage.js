// historyStorage.js — chat history persistence, backed by IndexedDB instead
// of localStorage.
//
// WHY: localStorage has a hard ~5-10MB per-origin ceiling. A single
// variance_table (comparative analysis) message can carry every comparable
// fact in a return (varianceAll) and alone exceed that ceiling on a
// realistic comparison, which made localStorage.setItem() throw
// QuotaExceededError and silently stop persisting ANY further history.
// IndexedDB's quota is a share of free disk space (typically hundreds of MB
// to several GB per origin), which comfortably covers this without ever
// trimming/dropping conversation content.
//
// One record per historyId (see App.jsx's _historyId — unchanged: still
// _loginId || _uid || an anonymous per-browser id), holding that
// conversation's full `messages` array exactly as App.jsx already builds it
// — no change to the message shape, only to where the array is written.

const DB_NAME    = 'chatbot-history'
const DB_VERSION = 1
const STORE_NAME  = 'histories'
// Key each record is stored under — matches the existing localStorage key
// naming (`chat_history_${historyId}`) purely so the migration step below
// can find prior data; the IndexedDB key itself is just historyId.
const LS_KEY_PREFIX = 'chat_history_'

// M-32: previously unbounded -- saveHistory() put() the entire messages
// array every time with no cap, so a very long-running conversation (or
// one with large comparative-analysis payloads) could grow a single
// IndexedDB record indefinitely. Keeps only the most recent N messages;
// oldest ones are dropped, not the newest.
export const MAX_STORED_MESSAGES = 200

let _dbPromise = null

function _openDatabase() {
  if (_dbPromise) return _dbPromise
  _dbPromise = new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('IndexedDB is not available in this browser/context'))
      return
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'historyId' })
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error || new Error('IndexedDB open failed'))
    request.onblocked = () => reject(new Error('IndexedDB open blocked (another tab holds an older version)'))
  })
  // A failed open must not permanently wedge every future call behind the
  // same rejected promise — the next caller gets a fresh attempt.
  _dbPromise.catch(() => { _dbPromise = null })
  return _dbPromise
}

function _runTransaction(mode, work) {
  return _openDatabase().then((db) => new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, mode)
    const store = tx.objectStore(STORE_NAME)
    let result
    tx.oncomplete = () => resolve(result)
    tx.onerror = () => reject(tx.error || new Error('IndexedDB transaction failed'))
    tx.onabort = () => reject(tx.error || new Error('IndexedDB transaction aborted'))
    try {
      result = work(store)
    } catch (err) {
      reject(err)
    }
  }))
}

function _requestToPromise(request) {
  // Only used INSIDE _runTransaction's `work` callback — the surrounding
  // transaction's oncomplete/onerror is what actually resolves/rejects the
  // outer promise; this just gives `work` a value to hand back as `result`.
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

// ── One-time localStorage -> IndexedDB migration ────────────────────────────
// Safe by construction: only runs from loadHistory() when IndexedDB has NO
// record yet for this historyId (never overwrites newer IndexedDB data), and
// the old localStorage key is removed only after the IndexedDB write is
// confirmed to have committed — never before.
function _migrateFromLocalStorage(historyId) {
  let raw
  try {
    raw = localStorage.getItem(LS_KEY_PREFIX + historyId)
  } catch {
    return null  // private-browsing/storage-denied — nothing to migrate
  }
  if (!raw) return null
  let parsed
  try {
    parsed = JSON.parse(raw)
  } catch {
    return null  // corrupted old data — not worth propagating the corruption
  }
  if (!Array.isArray(parsed) || parsed.length === 0) return null
  return parsed
}

/**
 * Load the message array for *historyId*, or null if none exists yet.
 * Transparently migrates a pre-existing localStorage entry on first read.
 */
export async function loadHistory(historyId) {
  if (!historyId) return null
  const existing = await _runTransaction('readonly', (store) => (
    _requestToPromise(store.get(historyId))
  ))
  if (existing) return existing.messages

  const migrated = _migrateFromLocalStorage(historyId)
  if (!migrated) return null

  // Write the migrated data into IndexedDB, then — and only then — remove
  // the old localStorage entry, so a failure here leaves the original data
  // exactly where it already was rather than losing it.
  await saveHistory(historyId, migrated)
  try { localStorage.removeItem(LS_KEY_PREFIX + historyId) } catch { /* ignore */ }
  return migrated
}

/** Persist *messages* under *historyId*, replacing whatever was there.
 * M-32: bounded to the most recent MAX_STORED_MESSAGES entries. */
export async function saveHistory(historyId, messages) {
  if (!historyId) return
  const bounded = Array.isArray(messages) && messages.length > MAX_STORED_MESSAGES
    ? messages.slice(messages.length - MAX_STORED_MESSAGES)
    : messages
  await _runTransaction('readwrite', (store) => (
    _requestToPromise(store.put({ historyId, messages: bounded, updatedAt: Date.now() }))
  ))
}

/** Remove the stored history for *historyId* (Clear Chat / logout). */
export async function deleteHistory(historyId) {
  if (!historyId) return
  await _runTransaction('readwrite', (store) => (
    _requestToPromise(store.delete(historyId))
  ))
  // Also drop any not-yet-migrated localStorage copy so a stale pre-IndexedDB
  // entry can never resurface for this historyId after an explicit delete.
  try { localStorage.removeItem(LS_KEY_PREFIX + historyId) } catch { /* ignore */ }
}
