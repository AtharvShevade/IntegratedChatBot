/**
 * i18n.js — centralized static UI text for the chatbot.
 *
 * STATIC vs DYNAMIC — the whole point of this file:
 *
 *   STATIC  (here)   Text predefined in the code: the welcome card, menu
 *                    labels, buttons, placeholders, fixed error strings.
 *                    Looked up from this dictionary. ZERO LLM calls, zero
 *                    latency, deterministic wording every time.
 *
 *   DYNAMIC (server) Chatbot responses generated at runtime. Those still go
 *                    through backend/i18n (TRANSLATION_MODEL), unchanged.
 *
 *   DATA    (never)  Return/report names, CIMS_ROR, DBR01, RAQ(Quarterly),
 *                    IDs, dates, numbers, options[], SQL/data fields. These
 *                    are never translated anywhere, by anything.
 *
 * ── The rule that must not be broken ──────────────────────────────────────
 *
 * The six action strings ("Check report status", ...) are BOTH a display
 * label and a PROTOCOL TOKEN. backend/guided.py:179-180 matches them with
 * `msg in GUIDED_ACTIONS` — an exact English literal test — and
 * getAllowedActions() filters on the same English strings.
 *
 * So ACTIONS below maps  English token -> localized label.  The token is the
 * key and is what gets SENT; only the value is ever shown. Never send a
 * translated label to the backend, and never key anything off a label.
 *
 * Emphasis: a `*starred*` span in a string renders bold (see renderRich).
 * Kept inside the string so each language controls its own word order.
 */

import { UI } from './i18n.ui.js'
export { UI }

export const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'fr', label: 'Français' },
  { code: 'ar', label: 'العربية' },
  { code: 'hi', label: 'हिन्दी' },
]

export const RTL_LANGUAGES = new Set(['ar'])

/** Localized labels for the six guided actions, keyed by their ENGLISH token. */
export const ACTIONS = {
  'Check report status': {
    en: 'Check report status',
    fr: 'Vérifier le statut du rapport',
    ar: 'التحقق من حالة التقرير',
    hi: 'रिपोर्ट की स्थिति जांचें',
  },
  'Generate instance for a report': {
    en: 'Generate instance for a report',
    fr: 'Générer une instance de rapport',
    ar: 'إنشاء نسخة لتقرير',
    hi: 'रिपोर्ट के लिए इंस्टेंस बनाएँ',
  },
  'Schedule a report': {
    en: 'Schedule a report',
    fr: 'Planifier un rapport',
    ar: 'جدولة تقرير',
    hi: 'रिपोर्ट शेड्यूल करें',
  },
  'Perform comparative analysis': {
    en: 'Perform comparative analysis',
    fr: 'Effectuer une analyse comparative',
    ar: 'إجراء تحليل مقارن',
    hi: 'तुलनात्मक विश्लेषण करें',
  },
  'Retrieve data from database': {
    en: 'Retrieve data from database',
    fr: 'Extraire des données de la base de données',
    ar: 'استرجاع البيانات من قاعدة البيانات',
    hi: 'डेटाबेस से डेटा प्राप्त करें',
  },
}

/** One-line descriptions under each action in the guided menu. */
export const ACTION_DESCRIPTIONS = {
  'Check report status': {
    en: 'Look up the latest status of any report',
    fr: 'Consulter le dernier statut de n’importe quel rapport',
    ar: 'الاطلاع على آخر حالة لأي تقرير',
    hi: 'किसी भी रिपोर्ट की नवीनतम स्थिति देखें',
  },
  'Generate instance for a report': {
    en: 'Trigger a new report instance for a period',
    fr: 'Déclencher une nouvelle instance de rapport pour une période',
    ar: 'تشغيل نسخة تقرير جديدة لفترة محددة',
    hi: 'किसी अवधि के लिए नई रिपोर्ट इंस्टेंस चलाएँ',
  },
  'Schedule a report': {
    en: 'Schedule a report to run at a future date/time',
    fr: 'Planifier l’exécution d’un rapport à une date/heure future',
    ar: 'جدولة تشغيل تقرير في تاريخ/وقت مستقبلي',
    hi: 'भविष्य की तिथि/समय पर रिपोर्ट चलाने के लिए शेड्यूल करें',
  },
  'Perform comparative analysis': {
    en: 'Compare two report instances period-over-period',
    fr: 'Comparer deux instances de rapport d’une période à l’autre',
    ar: 'مقارنة نسختَي تقرير بين فترتين',
    hi: 'दो रिपोर्ट इंस्टेंस की अवधि-दर-अवधि तुलना करें',
  },
  'Retrieve data from database': {
    en: 'Query the database using plain English',
    fr: 'Interroger la base de données en langage courant',
    ar: 'الاستعلام عن قاعدة البيانات بلغة بسيطة',
    hi: 'सरल भाषा में डेटाबेस से पूछें',
  },
}

/**
 * Localized labels for COMMAND options, keyed by their ENGLISH value.
 *
 * options[] carries two different kinds of thing, and they must be handled
 * differently:
 *
 *   COMMAND options  a fixed, code-defined set the user reads and clicks --
 *                    "Schedule", "Change Data", "Yes", "No"
 *                    (agent/__init__.py:1514, :3253, :3464, :3686).
 *                    Genuinely static UI text, so it is localized HERE with
 *                    zero LLM calls.
 *
 *   DATA options     report/return/instance names from the repository --
 *                    CIMS_ROR, RAQ(Quarterly), "31-Mar-2026 | Completed".
 *                    NEVER translated, by anything.
 *
 * t.option() distinguishes them by lookup: a value absent from this table is
 * returned unchanged, so data options pass through untouched by construction.
 *
 * As with ACTIONS, the KEY is the wire value. agent/__init__.py:1443-1457
 * matches the reply with `raw == "schedule"` and `"change" in raw` on the
 * lower-cased English text, so the click must always send the English key.
 */
export const OPTION_LABELS = {
  'Schedule': {
    en: 'Schedule', fr: 'Planifier', ar: 'جدولة', hi: 'शेड्यूल करें',
  },
  'Change Data': {
    en: 'Change Data', fr: 'Modifier les données',
    ar: 'تغيير البيانات', hi: 'डेटा बदलें',
  },
  'Yes': { en: 'Yes', fr: 'Oui', ar: 'نعم', hi: 'हाँ' },
  'No':  { en: 'No',  fr: 'Non', ar: 'لا',  hi: 'नहीं' },
}

/** Everything else. Keys are stable identifiers, never displayed. */
export const STRINGS = {
  // ── Welcome card ────────────────────────────────────────────────────────
  welcomeGreeting: {
    en: '👋 Hi! I’m your Report Assistant.',
    fr: '👋 Bonjour ! Je suis votre assistant de rapports.',
    ar: '👋 مرحبًا! أنا مساعد التقارير الخاص بك.',
    hi: '👋 नमस्ते! मैं आपका रिपोर्ट सहायक हूँ।',
  },
  welcomeHelp: {
    en: 'I can help you with:',
    fr: 'Je peux vous aider à :',
    ar: 'يمكنني مساعدتك في:',
    hi: 'मैं आपकी इनमें मदद कर सकता हूँ:',
  },
  welcomeItemStatus: {
    en: 'Checking the *status* of a report',
    fr: 'Vérifier le *statut* d’un rapport',
    ar: 'التحقق من *حالة* تقرير',
    hi: 'किसी रिपोर्ट की *स्थिति* जांचना',
  },
  welcomeItemGenerate: {
    en: '*Generating* a new report instance for a date',
    fr: '*Générer* une nouvelle instance de rapport pour une date',
    ar: '*إنشاء* نسخة تقرير جديدة لتاريخ محدد',
    hi: 'किसी तिथि के लिए नई रिपोर्ट इंस्टेंस *बनाना*',
  },
  welcomeItemSchedule: {
    en: '*Scheduling* reports for a future date and time',
    fr: '*Planifier* des rapports pour une date et une heure futures',
    ar: '*جدولة* التقارير لتاريخ ووقت مستقبليين',
    hi: 'भविष्य की तिथि और समय के लिए रिपोर्ट *शेड्यूल* करना',
  },
  welcomeItemCompare: {
    en: 'Performing *comparative analysis* on report instances',
    fr: 'Effectuer une *analyse comparative* sur des instances de rapport',
    ar: 'إجراء *تحليل مقارن* على نسخ التقارير',
    hi: 'रिपोर्ट इंस्टेंस पर *तुलनात्मक विश्लेषण* करना',
  },
  welcomeItemDatabase: {
    en: 'Retrieving data from the *database*',
    fr: 'Extraire des données de la *base de données*',
    ar: 'استرجاع البيانات من *قاعدة البيانات*',
    hi: '*डेटाबेस* से डेटा प्राप्त करना',
  },
  welcomeItemErrors: {
    en: '*Explaining errors* in a failed report instance',
    fr: '*Expliquer les erreurs* d’une instance de rapport en échec',
    ar: '*شرح الأخطاء* في نسخة تقرير فاشلة',
    hi: 'विफल रिपोर्ट इंस्टेंस में *त्रुटियाँ समझाना*',
  },
  welcomeCta: {
    en: 'Click a category to use guided mode, or type freely:',
    fr: 'Cliquez sur une catégorie pour le mode guidé, ou écrivez librement :',
    ar: 'انقر على فئة لاستخدام الوضع الموجّه، أو اكتب بحرية:',
    hi: 'गाइडेड मोड के लिए किसी श्रेणी पर क्लिक करें, या स्वतंत्र रूप से लिखें:',
  },

  // ── Menus ───────────────────────────────────────────────────────────────
  actionMenuPrompt: {
    en: 'What would you like to do next?',
    fr: 'Que souhaitez-vous faire ensuite ?',
    ar: 'ماذا تريد أن تفعل بعد ذلك؟',
    hi: 'आप आगे क्या करना चाहेंगे?',
  },
  startGuidedFlow: {
    en: 'Start guided flow',
    fr: 'Démarrer le mode guidé',
    ar: 'بدء الوضع الموجّه',
    hi: 'गाइडेड मोड शुरू करें',
  },
  guidedBadge: {
    en: '🧭 Guided', fr: '🧭 Guidé', ar: '🧭 موجّه', hi: '🧭 गाइडेड',
  },
  guidedModeIndicator: {
    en: '🧭 Guided mode — answer the question above',
    fr: '🧭 Mode guidé — répondez à la question ci-dessus',
    ar: '🧭 الوضع الموجّه — أجب عن السؤال أعلاه',
    hi: '🧭 गाइडेड मोड — ऊपर दिए गए प्रश्न का उत्तर दें',
  },

  // ── Input bar ───────────────────────────────────────────────────────────
  inputPlaceholder: {
    en: 'Ask about a report… or press the mic',
    fr: 'Posez une question sur un rapport… ou appuyez sur le micro',
    ar: 'اسأل عن تقرير… أو اضغط على الميكروفون',
    hi: 'किसी रिपोर्ट के बारे में पूछें… या माइक दबाएँ',
  },
  inputPlaceholderGuided: {
    en: 'Type your answer…',
    fr: 'Saisissez votre réponse…',
    ar: 'اكتب إجابتك…',
    hi: 'अपना उत्तर लिखें…',
  },
  clearChat: {
    en: 'Clear chat history',
    fr: 'Effacer l’historique de la conversation',
    ar: 'مسح سجل المحادثة',
    hi: 'चैट इतिहास साफ़ करें',
  },
  stopGenerating: {
    en: 'Stop generating',
    fr: 'Arrêter la génération',
    ar: 'إيقاف التوليد',
    hi: 'जनरेशन रोकें',
  },
  sendMessage: {
    en: 'Send message',
    fr: 'Envoyer le message',
    ar: 'إرسال الرسالة',
    hi: 'संदेश भेजें',
  },
  chatLanguage: {
    en: 'Chat language',
    fr: 'Langue de la conversation',
    ar: 'لغة المحادثة',
    hi: 'चैट की भाषा',
  },

  // ── Fixed status / error messages ───────────────────────────────────────
  errorGeneric: {
    en: 'Something went wrong. Please try again.',
    fr: 'Une erreur s’est produite. Veuillez réessayer.',
    ar: 'حدث خطأ ما. يرجى المحاولة مرة أخرى.',
    hi: 'कुछ गलत हो गया. कृपया पुनः प्रयास करें.',
  },
  errorComparison: {
    en: 'Comparison failed. Please try again.',
    fr: 'La comparaison a échoué. Veuillez réessayer.',
    ar: 'فشلت المقارنة. يرجى المحاولة مرة أخرى.',
    hi: 'तुलना विफल रही. कृपया पुनः प्रयास करें.',
  },
  errorExplanations: {
    en: 'Failed to generate explanations. Please try again.',
    fr: 'Échec de la génération des explications. Veuillez réessayer.',
    ar: 'تعذّر إنشاء التفسيرات. يرجى المحاولة مرة أخرى.',
    hi: 'स्पष्टीकरण बनाने में विफल. कृपया पुनः प्रयास करें.',
  },
  noDataFound: {
    en: 'No data found.',
    fr: 'Aucune donnée trouvée.',
    ar: 'لم يتم العثور على بيانات.',
    hi: 'कोई डेटा नहीं मिला.',
  },
  wasThisHelpful: {
    en: 'Was this helpful?',
    fr: 'Cette réponse vous a-t-elle été utile ?',
    ar: 'هل كان هذا مفيدًا؟',
    hi: 'क्या यह सहायक था?',
  },

  // ── Pickers / tables ────────────────────────────────────────────────────
  selectReportName: {
    en: 'Select Report Name',
    fr: 'Sélectionner le nom du rapport',
    ar: 'اختر اسم التقرير',
    hi: 'रिपोर्ट का नाम चुनें',
  },
  typeToFilter: {
    en: 'Type to filter…',
    fr: 'Filtrer…',
    ar: 'اكتب للتصفية…',
    hi: 'फ़िल्टर करने के लिए लिखें…',
  },
  checkAnotherDate: {
    en: 'Would you also like to check status for another reporting date?',
    fr: 'Souhaitez-vous aussi vérifier le statut pour une autre date de déclaration ?',
    ar: 'هل تود أيضًا التحقق من الحالة لتاريخ تقرير آخر؟',
    hi: 'क्या आप किसी अन्य रिपोर्टिंग तिथि के लिए भी स्थिति जांचना चाहेंगे?',
  },
  prev: { en: 'Prev', fr: 'Préc.', ar: 'السابق', hi: 'पिछला' },
  next: { en: 'Next', fr: 'Suiv.', ar: 'التالي', hi: 'अगला' },
  records: { en: 'records', fr: 'enregistrements', ar: 'سجلات', hi: 'रिकॉर्ड' },
}

const FALLBACK = 'en'

/**
 * Look up a static string. Falls back to English for a missing language or a
 * missing key, so a gap in the dictionary degrades to English rather than
 * rendering `undefined` at the user.
 */
export function translate(dict, key, lang) {
  const entry = dict[key]
  if (!entry) return key
  return entry[lang] ?? entry[FALLBACK] ?? key
}

/**
 * Bind a language once: `const t = makeT(lang)` then `t('welcomeHelp')`.
 *
 * One lookup for the whole application, not two systems: chatbot keys live in
 * STRINGS, application-wide UI keys in UI (i18n.ui.js), and t() checks both.
 * STRINGS wins on a collision so existing chatbot keys can never be shadowed.
 */
export function makeT(lang) {
  const t = (key) => (key in STRINGS
    ? translate(STRINGS, key, lang)
    : translate(UI, key, lang))
  // Both keyed by the ENGLISH action token — never by a localized label.
  t.action = (englishToken) => translate(ACTIONS, englishToken, lang)
  t.actionDesc = (englishToken) => translate(ACTION_DESCRIPTIONS, englishToken, lang)
  // Command options localize; data options (report names, instance labels)
  // are absent from OPTION_LABELS and come back unchanged.
  t.option = (englishValue) => translate(OPTION_LABELS, englishValue, lang)
  // Echo of the user's own message. When they CLICKED a button, the bubble
  // holds the English protocol token that was sent ("Generate instance for a
  // report", "Schedule"); show them the label they actually read. Free text
  // they typed themselves is in neither table and comes back untouched.
  t.echo = (value) => {
    if (value in ACTIONS) return translate(ACTIONS, value, lang)
    if (value in OPTION_LABELS) return translate(OPTION_LABELS, value, lang)
    return value
  }
  t.lang = lang
  t.dir = RTL_LANGUAGES.has(lang) ? 'rtl' : 'ltr'
  return t
}

export function isRtl(lang) {
  return RTL_LANGUAGES.has(lang)
}

// ── React binding ──────────────────────────────────────────────────────────
// A context rather than props: MessageBubble sits several levels down and
// threading `lang` through ChatWindow into every card would touch far more
// code than the strings themselves. Default 'en' means a component rendered
// outside the provider (a test, a future embed) still renders English.
import { createContext, useContext } from 'react'

export const LanguageContext = createContext(FALLBACK)

/** `const t = useT()` inside any component under the provider. */
export function useT() {
  return makeT(useContext(LanguageContext))
}
