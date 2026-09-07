/**
 * i18n.ui.js — application-wide static UI text.
 *
 * Flat dotted keys, namespaced BY FEATURE so related labels sit together and
 * each concept is defined exactly once. `common.*` holds the shared verbs and
 * nouns; nothing below it re-defines Cancel, Close, Status, Date and friends.
 *
 * Reached through the same t() as the rest of i18n.js:
 *
 *     t('comparativeAnalysis.columns.concept')
 *
 * Zero model calls — a dictionary lookup, exactly like i18n.js. Missing keys
 * or languages fall back to English rather than rendering `undefined`.
 *
 * What is DELIBERATELY absent, because it is DATA or a WIRE VALUE:
 *   • report/return names, instance labels, concept names (`labelA`, `labelB`,
 *     `row.concept`) — these come from the repository
 *   • dates, times, numbers, currency, GUIDs
 *   • SQL text and the Oracle column headers in `db_columns`
 *   • the English protocol tokens in ACTIONS / OPTION_LABELS (i18n.js)
 * Translating any of those would corrupt the data or break the backend
 * matcher; only presentation labels live here.
 */

export const UI = {
  // ── common: shared across every surface, defined once ────────────────────
  'common.cancel':       { en: 'Cancel', fr: 'Annuler', ar: 'إلغاء', hi: 'रद्द करें' },
  'common.close':        { en: 'Close', fr: 'Fermer', ar: 'إغلاق', hi: 'बंद करें' },
  'common.save':         { en: 'Save', fr: 'Enregistrer', ar: 'حفظ', hi: 'सहेजें' },
  'common.back':         { en: 'Back', fr: 'Retour', ar: 'رجوع', hi: 'वापस' },
  'common.submit':       { en: 'Submit', fr: 'Envoyer', ar: 'إرسال', hi: 'सबमिट करें' },
  'common.search':       { en: 'Search', fr: 'Rechercher', ar: 'بحث', hi: 'खोजें' },
  'common.filter':       { en: 'Filter', fr: 'Filtrer', ar: 'تصفية', hi: 'फ़िल्टर' },
  'common.export':       { en: 'Export', fr: 'Exporter', ar: 'تصدير', hi: 'निर्यात' },
  'common.download':     { en: 'Download', fr: 'Télécharger', ar: 'تنزيل', hi: 'डाउनलोड' },
  'common.refresh':      { en: 'Refresh', fr: 'Actualiser', ar: 'تحديث', hi: 'रिफ़्रेश' },
  'common.status':       { en: 'Status', fr: 'Statut', ar: 'الحالة', hi: 'स्थिति' },
  'common.date':         { en: 'Date', fr: 'Date', ar: 'التاريخ', hi: 'तिथि' },
  'common.name':         { en: 'Name', fr: 'Nom', ar: 'الاسم', hi: 'नाम' },
  'common.actions':      { en: 'Actions', fr: 'Actions', ar: 'الإجراءات', hi: 'क्रियाएँ' },
  'common.all':          { en: 'All', fr: 'Tout', ar: 'الكل', hi: 'सभी' },
  'common.showing':      { en: 'Showing', fr: 'Affichage de', ar: 'عرض', hi: 'दिखा रहे हैं' },
  'common.of':           { en: 'of', fr: 'sur', ar: 'من', hi: 'में से' },
  'common.rows':         { en: 'Rows', fr: 'Lignes', ar: 'الصفوف', hi: 'पंक्तियाँ' },
  'common.show':         { en: 'Show', fr: 'Afficher', ar: 'إظهار', hi: 'दिखाएँ' },
  'common.loading':      { en: 'Loading…', fr: 'Chargement…', ar: 'جارٍ التحميل…', hi: 'लोड हो रहा है…' },
  'common.generating':   { en: 'Generating…', fr: 'Génération…', ar: 'جارٍ الإنشاء…', hi: 'बनाया जा रहा है…' },
  'common.select':       { en: 'Select', fr: 'Sélectionner', ar: 'اختيار', hi: 'चुनें' },
  'common.you':          { en: 'You', fr: 'Vous', ar: 'أنت', hi: 'आप' },
  'common.notAvailable': { en: 'N/A', fr: 'S.O.', ar: 'غير متاح', hi: 'लागू नहीं' },
  'comparativeAnalysis.extreme': { en: 'Extreme', fr: 'Extrême', ar: 'متطرف', hi: 'अत्यधिक' },
  'common.clearFilters': { en: 'Clear filters', fr: 'Effacer les filtres', ar: 'مسح عوامل التصفية', hi: 'फ़िल्टर साफ़ करें' },

  // ── status: closed set, mirrors report_lookup._STATUS_LABELS ─────────────
  // The backend VALUE is unchanged; only these display labels are localized.
  'status.approvalPending': { en: 'Approval Pending', fr: 'En attente d’approbation', ar: 'في انتظار الموافقة', hi: 'अनुमोदन लंबित' },
  'status.approved':        { en: 'Approved', fr: 'Approuvé', ar: 'معتمد', hi: 'अनुमोदित' },
  'status.failed':          { en: 'Failed', fr: 'Échec', ar: 'فشل', hi: 'विफल' },
  'status.inProcess':       { en: 'In Process', fr: 'En cours', ar: 'قيد المعالجة', hi: 'प्रक्रियाधीन' },
  'status.inQueue':         { en: 'In Queue', fr: 'En file d’attente', ar: 'في قائمة الانتظار', hi: 'कतार में' },
  'status.unknown':         { en: 'Unknown', fr: 'Inconnu', ar: 'غير معروف', hi: 'अज्ञात' },
  'status.completed':       { en: 'Completed', fr: 'Terminé', ar: 'مكتمل', hi: 'पूर्ण' },

  // ── comparativeAnalysis: variance dashboard, table and chart modal ───────
  'comparativeAnalysis.title':            { en: 'Variance Visualisation', fr: 'Visualisation des écarts', ar: 'عرض الفروقات', hi: 'भिन्नता विज़ुअलाइज़ेशन' },
  'comparativeAnalysis.chartTitle':       { en: 'Variance Chart', fr: 'Graphique des écarts', ar: 'مخطط الفروقات', hi: 'भिन्नता चार्ट' },
  'comparativeAnalysis.aiAnalysis':       { en: 'AI Analysis', fr: 'Analyse IA', ar: 'تحليل الذكاء الاصطناعي', hi: 'AI विश्लेषण' },
  'comparativeAnalysis.visualize':        { en: 'Visualize', fr: 'Visualiser', ar: 'عرض بياني', hi: 'विज़ुअलाइज़ करें' },
  'comparativeAnalysis.openChart':        { en: 'Open chart visualisation', fr: 'Ouvrir la visualisation graphique', ar: 'فتح العرض البياني', hi: 'चार्ट विज़ुअलाइज़ेशन खोलें' },
  'comparativeAnalysis.closeChart':       { en: 'Close chart', fr: 'Fermer le graphique', ar: 'إغلاق المخطط', hi: 'चार्ट बंद करें' },
  'comparativeAnalysis.stopAnalysis':     { en: 'Stop generating the AI analysis', fr: 'Arrêter la génération de l’analyse IA', ar: 'إيقاف إنشاء تحليل الذكاء الاصطناعي', hi: 'AI विश्लेषण बनाना रोकें' },
  'comparativeAnalysis.compareInstances': { en: 'Compare Instances', fr: 'Comparer les instances', ar: 'مقارنة النسخ', hi: 'इंस्टेंस की तुलना करें' },
  'comparativeAnalysis.instance1':        { en: 'Instance 1', fr: 'Instance 1', ar: 'النسخة 1', hi: 'इंस्टेंस 1' },
  'comparativeAnalysis.instance2':        { en: 'Instance 2', fr: 'Instance 2', ar: 'النسخة 2', hi: 'इंस्टेंस 2' },

  // Table column headers. The COLUMN KEY (concept / val_a / val_b / diff /
  // pct) is unchanged — sorting and the API contract still use it. The
  // val_a / val_b headers are the INSTANCE LABELS and stay as data.
  'comparativeAnalysis.columns.concept':   { en: 'Concept', fr: 'Concept', ar: 'المفهوم', hi: 'अवधारणा' },
  'comparativeAnalysis.columns.diff':      { en: 'Diff', fr: 'Écart', ar: 'الفرق', hi: 'अंतर' },
  'comparativeAnalysis.columns.pctChange': { en: '% Chg', fr: '% Var.', ar: '% التغيّر', hi: '% परिवर्तन' },

  'comparativeAnalysis.searchConcept':      { en: 'Search concept…', fr: 'Rechercher un concept…', ar: 'ابحث عن مفهوم…', hi: 'अवधारणा खोजें…' },
  'comparativeAnalysis.searchConceptName':  { en: 'Search concept name…', fr: 'Rechercher un nom de concept…', ar: 'ابحث عن اسم مفهوم…', hi: 'अवधारणा का नाम खोजें…' },
  'comparativeAnalysis.filterTooltip':      { en: 'Filter the table by concept name', fr: 'Filtrer le tableau par nom de concept', ar: 'تصفية الجدول حسب اسم المفهوم', hi: 'अवधारणा नाम से तालिका फ़िल्टर करें' },
  'comparativeAnalysis.filterChartTooltip': { en: 'Filter the chart by concept name', fr: 'Filtrer le graphique par nom de concept', ar: 'تصفية المخطط حسب اسم المفهوم', hi: 'अवधारणा नाम से चार्ट फ़िल्टर करें' },
  'comparativeAnalysis.filterNoteTable':    { en: 'Filters which facts the table lists. Does not change the comparison.', fr: 'Filtre les faits listés dans le tableau. Ne modifie pas la comparaison.', ar: 'يصفّي الحقائق المعروضة في الجدول. لا يغيّر المقارنة.', hi: 'तालिका में दिखाए गए तथ्यों को फ़िल्टर करता है। तुलना नहीं बदलता।' },
  'comparativeAnalysis.filterNoteChart':    { en: 'Filters which facts the chart draws. Does not change the comparison.', fr: 'Filtre les faits tracés dans le graphique. Ne modifie pas la comparaison.', ar: 'يصفّي الحقائق المرسومة في المخطط. لا يغيّر المقارنة.', hi: 'चार्ट में बनाए गए तथ्यों को फ़िल्टर करता है। तुलना नहीं बदलता।' },
  'comparativeAnalysis.rowsNoteTable':      { en: 'How many rows to list. Display only — the comparison keeps every concept.', fr: 'Nombre de lignes à lister. Affichage seulement — la comparaison conserve tous les concepts.', ar: 'عدد الصفوف المعروضة. للعرض فقط — تحتفظ المقارنة بكل المفاهيم.', hi: 'कितनी पंक्तियाँ दिखानी हैं। केवल प्रदर्शन — तुलना हर अवधारणा रखती है।' },
  'comparativeAnalysis.rowsNoteChart':      { en: 'How many rows to draw, taken from the top of the current ranking.', fr: 'Nombre de lignes à tracer, prises en haut du classement actuel.', ar: 'عدد الصفوف المرسومة، من أعلى الترتيب الحالي.', hi: 'कितनी पंक्तियाँ बनानी हैं, वर्तमान रैंकिंग के शीर्ष से।' },
  'comparativeAnalysis.showPctChange':      { en: 'Show % change per concept', fr: 'Afficher la variation en % par concept', ar: 'إظهار نسبة التغيّر لكل مفهوم', hi: 'प्रति अवधारणा % परिवर्तन दिखाएँ' },
  'comparativeAnalysis.factsCompared':      { en: 'Facts compared', fr: 'Faits comparés', ar: 'الحقائق المقارنة', hi: 'तुलना किए गए तथ्य' },
  'comparativeAnalysis.comparableFacts':    { en: 'Comparable Facts', fr: 'Faits comparables', ar: 'الحقائق القابلة للمقارنة', hi: 'तुलनीय तथ्य' },
  'comparativeAnalysis.concepts':           { en: 'Concepts', fr: 'Concepts', ar: 'المفاهيم', hi: 'अवधारणाएँ' },
  'comparativeAnalysis.increased':          { en: 'Increased', fr: 'En hausse', ar: 'ارتفع', hi: 'बढ़ा' },
  'comparativeAnalysis.decreased':          { en: 'Decreased', fr: 'En baisse', ar: 'انخفض', hi: 'घटा' },
  'comparativeAnalysis.unchanged':          { en: 'Unchanged', fr: 'Inchangé', ar: 'دون تغيير', hi: 'अपरिवर्तित' },
  'comparativeAnalysis.reversed':           { en: 'Reversed', fr: 'Inversé', ar: 'معكوس', hi: 'उलटा' },
  'comparativeAnalysis.noChange':           { en: 'No Change', fr: 'Aucun changement', ar: 'لا تغيير', hi: 'कोई परिवर्तन नहीं' },
  'comparativeAnalysis.current':            { en: 'Current', fr: 'Actuel', ar: 'الحالي', hi: 'वर्तमान' },
  'comparativeAnalysis.previous':           { en: 'Previous', fr: 'Précédent', ar: 'السابق', hi: 'पिछला' },
  'comparativeAnalysis.importance':         { en: 'Importance', fr: 'Importance', ar: 'الأهمية', hi: 'महत्व' },
  'comparativeAnalysis.rankedBy':           { en: 'Ranked by', fr: 'Classé par', ar: 'مرتّب حسب', hi: 'क्रमबद्ध' },
  'comparativeAnalysis.inTier':             { en: 'in tier', fr: 'dans le niveau', ar: 'في المستوى', hi: 'श्रेणी में' },
  'comparativeAnalysis.downloadNote':       { en: 'Download always exports the full set.', fr: 'Le téléchargement exporte toujours l’ensemble complet.', ar: 'يصدّر التنزيل دائمًا المجموعة الكاملة.', hi: 'डाउनलोड हमेशा पूरा सेट निर्यात करता है।' },
  'comparativeAnalysis.noRows':             { en: 'No rows to display.', fr: 'Aucune ligne à afficher.', ar: 'لا توجد صفوف للعرض.', hi: 'दिखाने के लिए कोई पंक्ति नहीं।' },
  'comparativeAnalysis.noFactsMatch':       { en: 'No facts match this filter.', fr: 'Aucun fait ne correspond à ce filtre.', ar: 'لا توجد حقائق تطابق هذا الفلتر.', hi: 'इस फ़िल्टर से कोई तथ्य मेल नहीं खाता।' },
  'comparativeAnalysis.highVariance':       { en: 'High variance', fr: 'Écart élevé', ar: 'فرق كبير', hi: 'उच्च भिन्नता' },
  'comparativeAnalysis.bothPeriodsNote':    { en: 'The fact was reported in both periods — this is a real comparison, not missing data.', fr: 'Le fait a été déclaré sur les deux périodes — il s’agit d’une vraie comparaison, pas de données manquantes.', ar: 'تم الإبلاغ عن الحقيقة في كلتا الفترتين — هذه مقارنة حقيقية وليست بيانات مفقودة.', hi: 'यह तथ्य दोनों अवधियों में दर्ज किया गया — यह वास्तविक तुलना है, अनुपलब्ध डेटा नहीं।' },
  'comparativeAnalysis.zeroPreviousNote':   { en: 'Previous value was 0 — no % change (reported in both periods)', fr: 'La valeur précédente était 0 — pas de variation en % (déclarée sur les deux périodes)', ar: 'كانت القيمة السابقة 0 — لا نسبة تغيّر (مُبلغ عنها في كلتا الفترتين)', hi: 'पिछला मान 0 था — कोई % परिवर्तन नहीं (दोनों अवधियों में दर्ज)' },

  // Filter legend shared by the variance table and the chart modal.
  // The FILTER KEY ('all','sig','up','down','reversal','zero') is unchanged.
  'comparativeAnalysis.filters.allDesc':      { en: 'Every fact present in both periods', fr: 'Tous les faits présents sur les deux périodes', ar: 'كل حقيقة موجودة في كلتا الفترتين', hi: 'दोनों अवधियों में मौजूद हर तथ्य' },
  'comparativeAnalysis.filters.sigDesc':      { en: 'Facts flagged high-variance by the variance logic', fr: 'Faits signalés à écart élevé par la logique de variance', ar: 'الحقائق المصنّفة عالية الفروق وفق منطق الفروقات', hi: 'भिन्नता तर्क द्वारा उच्च-भिन्नता चिह्नित तथ्य' },
  'comparativeAnalysis.filters.upDesc':       { en: 'Current period is higher than the previous period', fr: 'La période actuelle est supérieure à la précédente', ar: 'الفترة الحالية أعلى من الفترة السابقة', hi: 'वर्तमान अवधि पिछली अवधि से अधिक है' },
  'comparativeAnalysis.filters.downDesc':     { en: 'Current period is lower than the previous period', fr: 'La période actuelle est inférieure à la précédente', ar: 'الفترة الحالية أقل من الفترة السابقة', hi: 'वर्तमान अवधि पिछली अवधि से कम है' },
  'comparativeAnalysis.filters.reversalDesc': { en: 'The value crossed zero — sign reversal', fr: 'La valeur a franchi zéro — inversion de signe', ar: 'تجاوزت القيمة الصفر — انعكاس الإشارة', hi: 'मान शून्य को पार कर गया — चिह्न उलटाव' },
  'comparativeAnalysis.filters.zero':         { en: 'Previous was 0', fr: 'Précédent était 0', ar: 'السابق كان 0', hi: 'पिछला 0 था' },


  // ── chart controls & legend ──────────────────────────────────────────────
  'comparativeAnalysis.downloadTooltip':{ en: 'Download a standalone HTML file with all {0} comparable facts', fr: 'Télécharger un fichier HTML autonome contenant les {0} faits comparables', ar: 'تنزيل ملف HTML مستقل يحتوي على جميع الحقائق القابلة للمقارنة البالغة {0}', hi: 'सभी {0} तुलनीय तथ्यों वाली स्वतंत्र HTML फ़ाइल डाउनलोड करें' },
  'comparativeAnalysis.chartBar':       { en: 'Bar', fr: 'Barres', ar: 'أعمدة', hi: 'बार' },
  'comparativeAnalysis.chartLine':      { en: 'Line', fr: 'Courbe', ar: 'خطي', hi: 'रेखा' },
  'comparativeAnalysis.legendIncrease': { en: 'Increase', fr: 'Hausse', ar: 'زيادة', hi: 'वृद्धि' },
  'comparativeAnalysis.legendDecrease': { en: 'Decrease', fr: 'Baisse', ar: 'انخفاض', hi: 'कमी' },
  'comparativeAnalysis.legendNoChange': { en: 'No change', fr: 'Aucun changement', ar: 'لا تغيير', hi: 'कोई परिवर्तन नहीं' },
  'comparativeAnalysis.legendReversedOutlined': { en: 'Reversed (outlined)', fr: 'Inversé (contour)', ar: 'معكوس (محدّد)', hi: 'उलटा (रूपरेखा)' },
  'comparativeAnalysis.directionReversed': { en: 'Direction reversed', fr: 'Sens inversé', ar: 'انعكس الاتجاه', hi: 'दिशा उलटी' },
  'comparativeAnalysis.veryHigh':       { en: 'Very High', fr: 'Très élevé', ar: 'مرتفع جدًا', hi: 'बहुत उच्च' },

  // ── ranking controls ─────────────────────────────────────────────────────
  'comparativeAnalysis.rankAbsoluteDiff':     { en: 'Absolute Diff', fr: 'Écart absolu', ar: 'الفرق المطلق', hi: 'निरपेक्ष अंतर' },
  'comparativeAnalysis.rankPctChange':        { en: '% Change', fr: '% de variation', ar: '% التغيّر', hi: '% परिवर्तन' },
  'comparativeAnalysis.rankAbsoluteDiffDesc': { en: 'Largest absolute difference first. Surfaces the biggest movements in value terms, regardless of how small they are in percentage terms.', fr: 'Écart absolu le plus élevé en premier. Fait ressortir les plus grands mouvements en valeur, quelle que soit leur faiblesse en pourcentage.', ar: 'الفرق المطلق الأكبر أولًا. يُبرز أكبر التحركات من حيث القيمة، مهما كانت صغيرة بالنسبة المئوية.', hi: 'सबसे बड़ा निरपेक्ष अंतर पहले। मूल्य के हिसाब से सबसे बड़े बदलाव सामने लाता है, चाहे प्रतिशत में वे कितने भी छोटे हों।' },
  'comparativeAnalysis.rankPctChangeDesc':    { en: 'Largest percentage movement first. Surfaces volatility — a small line that doubled outranks a large line that moved 3%.', fr: 'Variation en pourcentage la plus forte en premier. Fait ressortir la volatilité — une petite ligne qui a doublé passe devant une grande ligne ayant bougé de 3 %.', ar: 'أكبر تغيّر بالنسبة المئوية أولًا. يُبرز التقلب — بند صغير تضاعف يتقدّم على بند كبير تحرّك بنسبة 3%.', hi: 'सबसे बड़ा प्रतिशत बदलाव पहले। अस्थिरता सामने लाता है — दोगुनी हुई छोटी पंक्ति 3% चली बड़ी पंक्ति से ऊपर आती है।' },
  'comparativeAnalysis.defaultRanking':       { en: 'variance priority', fr: 'priorité de variance', ar: 'أولوية الفروقات', hi: 'भिन्नता प्राथमिकता' },
  'comparativeAnalysis.tierFilterTooltip':    { en: 'Filter by regulatory-importance tier from the return’s taxonomy JSON. Display only — the comparison keeps every concept.', fr: 'Filtrer par niveau d’importance réglementaire issu du JSON de taxonomie du rapport. Affichage seulement — la comparaison conserve tous les concepts.', ar: 'التصفية حسب مستوى الأهمية التنظيمية من ملف JSON الخاص بتصنيف التقرير. للعرض فقط — تحتفظ المقارنة بكل المفاهيم.', hi: 'रिपोर्ट की टैक्सोनॉमी JSON से नियामक-महत्व श्रेणी द्वारा फ़िल्टर करें। केवल प्रदर्शन — तुलना हर अवधारणा रखती है।' },

  // ── coverage caption: one template per shape, values inserted locally ─────
  'comparativeAnalysis.showingTopOf':      { en: 'Showing top {0} of {1}', fr: 'Affichage des {0} principaux sur {1}', ar: 'عرض أعلى {0} من {1}', hi: '{1} में से शीर्ष {0} दिखा रहे हैं' },
  'comparativeAnalysis.showingAll':        { en: 'Showing all {0}', fr: 'Affichage des {0}', ar: 'عرض جميع الـ {0}', hi: 'सभी {0} दिखा रहे हैं' },
  'comparativeAnalysis.comparableFacts':   { en: 'comparable facts', fr: 'faits comparables', ar: 'حقائق قابلة للمقارنة', hi: 'तुलनीय तथ्य' },
  'comparativeAnalysis.matchingFacts':     { en: 'matching facts', fr: 'faits correspondants', ar: 'حقائق مطابقة', hi: 'मेल खाते तथ्य' },
  'comparativeAnalysis.rankedBySep':       { en: 'ranked by', fr: 'classés par', ar: 'مرتّبة حسب', hi: 'क्रमबद्ध' },
  'comparativeAnalysis.tierSep':           { en: 'tier', fr: 'niveau', ar: 'المستوى', hi: 'श्रेणी' },
  'comparativeAnalysis.countUp':           { en: '{0} up', fr: '{0} en hausse', ar: '{0} ارتفعت', hi: '{0} बढ़े' },
  'comparativeAnalysis.countDown':         { en: '{0} down', fr: '{0} en baisse', ar: '{0} انخفضت', hi: '{0} घटे' },
  'comparativeAnalysis.countUnchanged':    { en: '{0} unchanged', fr: '{0} inchangés', ar: '{0} دون تغيير', hi: '{0} अपरिवर्तित' },
  'comparativeAnalysis.directionCountsNote': { en: '(direction counts cover all {0} facts)', fr: '(les compteurs de direction couvrent les {0} faits)', ar: '(تشمل عدادات الاتجاه جميع الحقائق البالغة {0})', hi: '(दिशा गणनाएँ सभी {0} तथ्यों को कवर करती हैं)' },
  'comparativeAnalysis.topN':              { en: 'Top {0}', fr: '{0} principaux', ar: 'أعلى {0}', hi: 'शीर्ष {0}' },
  'comparativeAnalysis.previousWas0Count': { en: 'Previous was 0 ({0})', fr: 'Précédent était 0 ({0})', ar: 'السابق كان 0 ({0})', hi: 'पिछला 0 था ({0})' },
  'comparativeAnalysis.everyFactDrawn':    { en: 'Every comparable fact is drawn below.', fr: 'Tous les faits comparables sont tracés ci-dessous.', ar: 'كل حقيقة قابلة للمقارنة مرسومة أدناه.', hi: 'हर तुलनीय तथ्य नीचे दिखाया गया है।' },
  'comparativeAnalysis.zeroBaselineNote':  { en: 'Reported in both periods, but the previous value was 0 — so there is no percentage change to compute. These are real comparisons, not missing facts.', fr: 'Déclarés sur les deux périodes, mais la valeur précédente était 0 — il n’y a donc aucune variation en pourcentage à calculer. Ce sont de vraies comparaisons, pas des faits manquants.', ar: 'مُبلغ عنها في كلتا الفترتين، لكن القيمة السابقة كانت 0 — لذا لا توجد نسبة تغيّر لحسابها. هذه مقارنات حقيقية وليست حقائق مفقودة.', hi: 'दोनों अवधियों में दर्ज, लेकिन पिछला मान 0 था — इसलिए गणना करने के लिए कोई प्रतिशत परिवर्तन नहीं है। ये वास्तविक तुलनाएँ हैं, अनुपलब्ध तथ्य नहीं।' },

  // ── chart tooltip ────────────────────────────────────────────────────────
  'comparativeAnalysis.tooltipCurrent':   { en: 'current', fr: 'actuel', ar: 'الحالي', hi: 'वर्तमान' },
  'comparativeAnalysis.tooltipPrevious':  { en: 'previous', fr: 'précédent', ar: 'السابق', hi: 'पिछला' },
  'comparativeAnalysis.exactChange':      { en: 'Exact change', fr: 'Variation exacte', ar: 'التغيّر الدقيق', hi: 'सटीक परिवर्तन' },
  'comparativeAnalysis.tooltipChange':    { en: 'Change', fr: 'Variation', ar: 'التغيّر', hi: 'परिवर्तन' },
  'comparativeAnalysis.tooltipDifference':{ en: 'Difference', fr: 'Écart', ar: 'الفرق', hi: 'अंतर' },
  'comparativeAnalysis.tooltipDirection': { en: 'Direction', fr: 'Sens', ar: 'الاتجاه', hi: 'दिशा' },
  'comparativeAnalysis.tooltipSignReversal': { en: 'Sign reversal', fr: 'Inversion de signe', ar: 'انعكاس الإشارة', hi: 'चिह्न उलटाव' },
  'comparativeAnalysis.sortHint':         { en: 'Click again to restore the default order.', fr: 'Cliquez à nouveau pour rétablir l’ordre par défaut.', ar: 'انقر مرة أخرى لاستعادة الترتيب الافتراضي.', hi: 'डिफ़ॉल्ट क्रम बहाल करने के लिए फिर से क्लिक करें।' },

  // ── exported HTML report ─────────────────────────────────────────────────
  'export.visualizationAll':   { en: 'Visualization: all {0} comparable facts', fr: 'Visualisation : les {0} faits comparables', ar: 'العرض المرئي: جميع الحقائق القابلة للمقارنة البالغة {0}', hi: 'विज़ुअलाइज़ेशन: सभी {0} तुलनीय तथ्य' },
  'export.oneSidedExcluded':   { en: '{0} fact(s) reported in only one period are excluded — they cannot be compared.', fr: '{0} fait(s) déclaré(s) sur une seule période sont exclus — ils ne peuvent pas être comparés.', ar: 'تم استبعاد {0} من الحقائق المُبلغ عنها في فترة واحدة فقط — لا يمكن مقارنتها.', hi: 'केवल एक अवधि में दर्ज {0} तथ्य बाहर रखे गए हैं — उनकी तुलना नहीं की जा सकती।' },
  'export.generatedFrom':      { en: 'Generated from the {0} Critical and High regulatory-importance concept(s) in this comparison.', fr: 'Généré à partir des {0} concept(s) d’importance réglementaire Critique et Élevée de cette comparaison.', ar: 'تم إنشاؤه من {0} من المفاهيم ذات الأهمية التنظيمية الحرجة والمرتفعة في هذه المقارنة.', hi: 'इस तुलना के {0} क्रिटिकल और उच्च नियामक-महत्व अवधारणाओं से बनाया गया।' },
  'export.graphLimitedCritical': { en: 'Graph limited to Critical regulatory-importance concepts.', fr: 'Graphique limité aux concepts d’importance réglementaire Critique.', ar: 'الرسم البياني مقتصر على المفاهيم ذات الأهمية التنظيمية الحرجة.', hi: 'ग्राफ़ केवल क्रिटिकल नियामक-महत्व अवधारणाओं तक सीमित।' },
  'export.criticalConcepts':   { en: 'Critical concepts', fr: 'Concepts critiques', ar: 'المفاهيم الحرجة', hi: 'क्रिटिकल अवधारणाएँ' },
  'export.currentVsPrevious':  { en: 'Current vs previous', fr: 'Actuel vs précédent', ar: 'الحالي مقابل السابق', hi: 'वर्तमान बनाम पिछला' },

  // ── errors / voice / misc UI ─────────────────────────────────────────────
  'errors.downloadReport':     { en: 'Download error report', fr: 'Télécharger le rapport d’erreurs', ar: 'تنزيل تقرير الأخطاء', hi: 'त्रुटि रिपोर्ट डाउनलोड करें' },
  'errors.explainFormula':     { en: 'Explain Formula Errors', fr: 'Expliquer les erreurs de formule', ar: 'شرح أخطاء الصيغة', hi: 'सूत्र त्रुटियाँ समझाएँ' },
  'errors.explainSchema':      { en: 'Explain Schema Errors', fr: 'Expliquer les erreurs de schéma', ar: 'شرح أخطاء المخطط', hi: 'स्कीमा त्रुटियाँ समझाएँ' },
  'errors.explainDimension':   { en: 'Explain Dimension Errors', fr: 'Expliquer les erreurs de dimension', ar: 'شرح أخطاء الأبعاد', hi: 'आयाम त्रुटियाँ समझाएँ' },
  'errors.failureReasons':     { en: 'Failure Reason(s):', fr: 'Motif(s) de l’échec :', ar: 'أسباب الفشل:', hi: 'विफलता के कारण:' },
  'errors.whatIsWrong':        { en: 'What is wrong', fr: 'Ce qui ne va pas', ar: 'ما الخطأ', hi: 'क्या गलत है' },
  'errors.whatShouldBeChecked':{ en: 'What should be checked', fr: 'Ce qu’il faut vérifier', ar: 'ما الذي ينبغي التحقق منه', hi: 'क्या जाँचना चाहिए' },
  'errors.reportedValue':      { en: 'Reported value', fr: 'Valeur déclarée', ar: 'القيمة المُبلغ عنها', hi: 'दर्ज किया गया मान' },
  'errors.sqlValidationFailed':{ en: 'SQL validation failed.', fr: 'La validation SQL a échoué.', ar: 'فشل التحقق من SQL.', hi: 'SQL सत्यापन विफल रहा।' },

  'variance.aiUnavailable':    { en: 'AI analysis is unavailable for this comparison. The variance table and chart above are complete.', fr: 'L’analyse IA n’est pas disponible pour cette comparaison. Le tableau et le graphique des écarts ci-dessus sont complets.', ar: 'تحليل الذكاء الاصطناعي غير متاح لهذه المقارنة. جدول الفروقات والمخطط أعلاه مكتملان.', hi: 'इस तुलना के लिए AI विश्लेषण उपलब्ध नहीं है। ऊपर दी गई भिन्नता तालिका और चार्ट पूर्ण हैं।' },
  'variance.chooseTwoInstances': { en: 'Choose two different instances to compare.', fr: 'Choisissez deux instances différentes à comparer.', ar: 'اختر نسختين مختلفتين للمقارنة.', hi: 'तुलना के लिए दो अलग-अलग इंस्टेंस चुनें।' },
  'variance.selectEachDropdown': { en: 'Select an instance in each dropdown.', fr: 'Sélectionnez une instance dans chaque liste déroulante.', ar: 'اختر نسخة من كل قائمة منسدلة.', hi: 'प्रत्येक ड्रॉपडाउन में एक इंस्टेंस चुनें।' },
  'variance.selectInstancePlaceholder': { en: '— Select instance —', fr: '— Sélectionner une instance —', ar: '— اختر نسخة —', hi: '— इंस्टेंस चुनें —' },
  'variance.noPctZeroBaseline':{ en: 'No % change (zero baseline)', fr: 'Aucune variation en % (base nulle)', ar: 'لا تغيّر بالنسبة المئوية (أساس صفري)', hi: 'कोई % परिवर्तन नहीं (शून्य आधार)' },
  'variance.toSeeEveryTier':   { en: 'to see every tier.', fr: 'pour voir tous les niveaux.', ar: 'لعرض جميع المستويات.', hi: 'सभी श्रेणियाँ देखने के लिए।' },

  'voice.micRequired':     { en: 'Microphone access is required to use voice input.', fr: 'L’accès au microphone est requis pour la saisie vocale.', ar: 'الوصول إلى الميكروفون مطلوب لاستخدام الإدخال الصوتي.', hi: 'वॉइस इनपुट के लिए माइक्रोफ़ोन एक्सेस आवश्यक है।' },
  'voice.transcribeFailed':{ en: 'Voice transcription failed. Please try again.', fr: 'La transcription vocale a échoué. Veuillez réessayer.', ar: 'فشل التفريغ الصوتي. يرجى المحاولة مرة أخرى.', hi: 'वॉइस ट्रांसक्रिप्शन विफल रहा। कृपया पुनः प्रयास करें।' },
  'voice.notHeard':        { en: 'We could not hear your speech clearly. Please try again.', fr: 'Nous n’avons pas bien entendu votre voix. Veuillez réessayer.', ar: 'لم نتمكن من سماع كلامك بوضوح. يرجى المحاولة مرة أخرى.', hi: 'हम आपकी आवाज़ स्पष्ट रूप से नहीं सुन सके। कृपया पुनः प्रयास करें।' },

  'errors.fetchActions':   { en: 'Failed to fetch allowed actions', fr: 'Échec de la récupération des actions autorisées', ar: 'تعذّر جلب الإجراءات المسموح بها', hi: 'अनुमत क्रियाएँ प्राप्त करने में विफल' },
  'errors.compareFailed':  { en: 'We could not compare those instances right now. Please try again.', fr: 'Nous n’avons pas pu comparer ces instances pour le moment. Veuillez réessayer.', ar: 'تعذّرت مقارنة هاتين النسختين حاليًا. يرجى المحاولة مرة أخرى.', hi: 'अभी उन इंस्टेंस की तुलना नहीं की जा सकी। कृपया पुनः प्रयास करें।' },
  'errors.explanationFailed': { en: 'We could not load the explanation right now. Please try again.', fr: 'Nous n’avons pas pu charger l’explication pour le moment. Veuillez réessayer.', ar: 'تعذّر تحميل الشرح حاليًا. يرجى المحاولة مرة أخرى.', hi: 'अभी स्पष्टीकरण लोड नहीं किया जा सका। कृपया पुनः प्रयास करें।' },
  'errors.requestFailed':  { en: 'We could not process your request right now. Please try again.', fr: 'Nous n’avons pas pu traiter votre demande pour le moment. Veuillez réessayer.', ar: 'تعذّرت معالجة طلبك حاليًا. يرجى المحاولة مرة أخرى.', hi: 'अभी आपका अनुरोध संसाधित नहीं किया जा सका। कृपया पुनः प्रयास करें।' },

  'common.disclaimer':     { en: 'AI-generated responses may be inaccurate — please verify important details against the application.', fr: 'Les réponses générées par l’IA peuvent être inexactes — veuillez vérifier les informations importantes dans l’application.', ar: 'قد تكون الردود المولّدة بالذكاء الاصطناعي غير دقيقة — يرجى التحقق من التفاصيل المهمة في التطبيق.', hi: 'AI-जनित उत्तर गलत हो सकते हैं — कृपया महत्वपूर्ण विवरण एप्लिकेशन में सत्यापित करें।' },

  'comparativeAnalysis.factsBoth':        { en: '{0} facts reported in BOTH {1} and {2}.', fr: '{0} faits déclarés dans {1} ET {2}.', ar: '{0} حقيقة مُبلغ عنها في كل من {1} و{2}.', hi: '{1} और {2} दोनों में दर्ज {0} तथ्य।' },
  'comparativeAnalysis.oneSidedExcluded': { en: '{0} present in only one period — excluded, they cannot be compared.', fr: '{0} présents sur une seule période — exclus, ils ne peuvent pas être comparés.', ar: '{0} موجودة في فترة واحدة فقط — مستبعدة، لا يمكن مقارنتها.', hi: '{0} केवल एक अवधि में मौजूद — बाहर रखे गए, उनकी तुलना नहीं की जा सकती।' },
  'comparativeAnalysis.dimensionalContext': { en: '{0} carry a dimensional context.', fr: '{0} portent un contexte dimensionnel.', ar: '{0} تحمل سياقًا بُعديًا.', hi: '{0} में आयामी संदर्भ है।' },
  'comparativeAnalysis.criticalConceptsOf': { en: 'Critical concepts — {0} of {1} facts', fr: 'Concepts critiques — {0} sur {1} faits', ar: 'المفاهيم الحرجة — {0} من {1} حقيقة', hi: 'क्रिटिकल अवधारणाएँ — {1} में से {0} तथ्य' },
  'comparativeAnalysis.currentVsPreviousAll': { en: 'Current vs previous — all {0} facts', fr: 'Actuel vs précédent — les {0} faits', ar: 'الحالي مقابل السابق — جميع الحقائق البالغة {0}', hi: 'वर्तमान बनाम पिछला — सभी {0} तथ्य' },
  'comparativeAnalysis.sortConcept':  { en: 'concept', fr: 'concept', ar: 'المفهوم', hi: 'अवधारणा' },
  'comparativeAnalysis.sortCurrent':  { en: 'current value', fr: 'valeur actuelle', ar: 'القيمة الحالية', hi: 'वर्तमान मान' },
  'comparativeAnalysis.sortPrevious': { en: 'previous value', fr: 'valeur précédente', ar: 'القيمة السابقة', hi: 'पिछला मान' },
  'comparativeAnalysis.sortDifference': { en: 'difference', fr: 'écart', ar: 'الفرق', hi: 'अंतर' },
  'comparativeAnalysis.sortPctChange':  { en: '% change', fr: '% de variation', ar: '% التغيّر', hi: '% परिवर्तन' },
  'comparativeAnalysis.sortSeverity':   { en: 'severity', fr: 'gravité', ar: 'الخطورة', hi: 'गंभीरता' },

  'comparativeAnalysis.rawDiff':          { en: 'Raw diff', fr: 'Écart brut', ar: 'الفرق الخام', hi: 'कच्चा अंतर' },
  'comparativeAnalysis.directionReversedLabel': { en: 'Direction reversed', fr: 'Sens inversé', ar: 'انعكس الاتجاه', hi: 'दिशा उलटी' },
  'comparativeAnalysis.zeroBaseTooltip':  { en: 'Previous period ({0}) was 0, so there is no percentage change to compute. The fact was reported in both periods — this is a real comparison, not missing data.', fr: 'La période précédente ({0}) était à 0, il n’y a donc aucune variation en pourcentage à calculer. Le fait a été déclaré sur les deux périodes — c’est une vraie comparaison, pas une donnée manquante.', ar: 'كانت الفترة السابقة ({0}) تساوي 0، لذا لا توجد نسبة تغيّر لحسابها. تم الإبلاغ عن الحقيقة في كلتا الفترتين — هذه مقارنة حقيقية وليست بيانات مفقودة.', hi: 'पिछली अवधि ({0}) 0 थी, इसलिए गणना करने के लिए कोई प्रतिशत परिवर्तन नहीं है। यह तथ्य दोनों अवधियों में दर्ज किया गया — यह वास्तविक तुलना है, अनुपलब्ध डेटा नहीं।' },
  'comparativeAnalysis.allCount':         { en: 'All ({0})', fr: 'Tout ({0})', ar: 'الكل ({0})', hi: 'सभी ({0})' },
  'errors.validationRuleFailed':          { en: "Validation rule '{0}' failed.", fr: 'La règle de validation « {0} » a échoué.', ar: 'فشلت قاعدة التحقق «{0}».', hi: "सत्यापन नियम '{0}' विफल रहा।" },
  'errors.ruleFailed':                    { en: "Rule '{0}' failed.", fr: 'La règle « {0} » a échoué.', ar: 'فشلت القاعدة «{0}».', hi: "नियम '{0}' विफल रहा।" },
  'errors.dimensionalDetected':           { en: "Dimensional error detected for concept '{0}'.", fr: 'Erreur dimensionnelle détectée pour le concept « {0} ».', ar: 'تم اكتشاف خطأ بُعدي للمفهوم «{0}».', hi: "अवधारणा '{0}' के लिए आयामी त्रुटि पाई गई।" },
  'errors.unknownConcept':                { en: 'unknown', fr: 'inconnu', ar: 'غير معروف', hi: 'अज्ञात' },
  'support.sorry':   { en: "I'm sorry the experience wasn't helpful.", fr: 'Je suis désolé que cette expérience n’ait pas été utile.', ar: 'يؤسفني أن التجربة لم تكن مفيدة.', hi: 'खेद है कि यह अनुभव सहायक नहीं रहा।' },
  'support.contact': { en: "If you're facing an issue, have a query, or want to report a problem, please contact our support team:", fr: 'Si vous rencontrez un problème, avez une question ou souhaitez signaler un incident, veuillez contacter notre équipe d’assistance :', ar: 'إذا كنت تواجه مشكلة أو لديك استفسار أو تريد الإبلاغ عن خلل، يرجى التواصل مع فريق الدعم:', hi: 'यदि आपको कोई समस्या है, प्रश्न है, या कोई परेशानी बतानी है, तो कृपया हमारी सहायता टीम से संपर्क करें:' },

  'comparativeAnalysis.moreRowsNotShown': { en: '{0} more rows not shown', fr: '{0} lignes supplémentaires non affichées', ar: '{0} صفوف إضافية غير معروضة', hi: '{0} और पंक्तियाँ नहीं दिखाई गईं' },
  'comparativeAnalysis.showAll':           { en: 'Show all {0}', fr: 'Afficher les {0}', ar: 'عرض الكل ({0})', hi: 'सभी {0} दिखाएँ' },

  'errors.summaryHeading':   { en: 'Error Summary', fr: 'Résumé des erreurs', ar: 'ملخص الأخطاء', hi: 'त्रुटि सारांश' },
  'errors.explainNext':      { en: 'Explain Next Errors', fr: 'Expliquer les erreurs suivantes', ar: 'شرح الأخطاء التالية', hi: 'अगली त्रुटियाँ समझाएँ' },

  // ── sql: the generated-SQL result block ──────────────────────────────────
  'sql.schemaMatch':    { en: 'Schema Match', fr: 'Correspondance de schéma', ar: 'تطابق المخطط', hi: 'स्कीमा मिलान' },
  'sql.generatedSql':   { en: 'Generated SQL', fr: 'SQL généré', ar: 'SQL المُنشأ', hi: 'जनरेट किया गया SQL' },
  'sql.queryResults':   { en: 'Query Results', fr: 'Résultats de la requête', ar: 'نتائج الاستعلام', hi: 'क्वेरी परिणाम' },
  'sql.noRowsReturned': { en: 'No rows returned.', fr: 'Aucune ligne renvoyée.', ar: 'لم تُرجع أي صفوف.', hi: 'कोई पंक्ति नहीं लौटी।' },
  'sql.needMoreDetail': { en: 'Need more detail:', fr: 'Plus de détails nécessaires :', ar: 'مطلوب مزيد من التفاصيل:', hi: 'अधिक विवरण आवश्यक:' },
  'sql.noMatches':      { en: 'No matches', fr: 'Aucune correspondance', ar: 'لا توجد مطابقات', hi: 'कोई मिलान नहीं' },

  // ── errors: validation-error panels and their tables ─────────────────────
  'errors.howToFix':            { en: 'How to fix', fr: 'Comment corriger', ar: 'كيفية الإصلاح', hi: 'कैसे ठीक करें' },
  'errors.dimensionalTitle':    { en: 'Dimensional Validation Errors', fr: 'Erreurs de validation dimensionnelle', ar: 'أخطاء التحقق البُعدي', hi: 'आयामी सत्यापन त्रुटियाँ' },
  'errors.columns.dbTableName': { en: 'DB Table Name', fr: 'Nom de table BD', ar: 'اسم جدول قاعدة البيانات', hi: 'DB तालिका नाम' },
  'errors.columns.rowLabel':    { en: 'Row Label', fr: 'Libellé de ligne', ar: 'تسمية الصف', hi: 'पंक्ति लेबल' },
  'errors.columns.rowLabels':   { en: 'Row Label(s)', fr: 'Libellé(s) de ligne', ar: 'تسمية/تسميات الصف', hi: 'पंक्ति लेबल' },
  'errors.columns.cellCode':    { en: 'Cell Code', fr: 'Code de cellule', ar: 'رمز الخلية', hi: 'सेल कोड' },
  'errors.columns.context':     { en: 'Context', fr: 'Contexte', ar: 'السياق', hi: 'संदर्भ' },
  'errors.columns.error':       { en: 'Error', fr: 'Erreur', ar: 'الخطأ', hi: 'त्रुटि' },
  'errors.columns.explanation': { en: 'Explanation', fr: 'Explication', ar: 'الشرح', hi: 'स्पष्टीकरण' },
  'errors.columns.item':        { en: 'Item', fr: 'Élément', ar: 'العنصر', hi: 'मद' },
  'errors.columns.expected':    { en: 'Expected', fr: 'Attendu', ar: 'المتوقع', hi: 'अपेक्षित' },
  'errors.columns.actual':      { en: 'Actual', fr: 'Réel', ar: 'الفعلي', hi: 'वास्तविक' },

  'errors.category.formulaError':       { en: 'Formula Error', fr: 'Erreur de formule', ar: 'خطأ في الصيغة', hi: 'सूत्र त्रुटि' },
  'errors.category.qualityCheck':       { en: 'Quality Check', fr: 'Contrôle qualité', ar: 'فحص الجودة', hi: 'गुणवत्ता जाँच' },
  'errors.category.specificationError': { en: 'Specification Error', fr: 'Erreur de spécification', ar: 'خطأ في المواصفات', hi: 'विनिर्देश त्रुटि' },
  'errors.category.schemaError':        { en: 'Schema Error', fr: 'Erreur de schéma', ar: 'خطأ في المخطط', hi: 'स्कीमा त्रुटि' },
  'errors.category.dimensionalError':   { en: 'Dimensional Error', fr: 'Erreur dimensionnelle', ar: 'خطأ بُعدي', hi: 'आयामी त्रुटि' },
  'errors.category.validationError':    { en: 'Validation Error', fr: 'Erreur de validation', ar: 'خطأ في التحقق', hi: 'सत्यापन त्रुटि' },
  'errors.category.formulaErrors':      { en: 'Formula Errors', fr: 'Erreurs de formule', ar: 'أخطاء الصيغة', hi: 'सूत्र त्रुटियाँ' },
  'errors.category.schemaErrors':       { en: 'Schema Errors', fr: 'Erreurs de schéma', ar: 'أخطاء المخطط', hi: 'स्कीमा त्रुटियाँ' },
  'errors.category.dimensionErrors':    { en: 'Dimension Errors', fr: 'Erreurs de dimension', ar: 'أخطاء الأبعاد', hi: 'आयाम त्रुटियाँ' },

  'errors.severity.critical': { en: 'Critical', fr: 'Critique', ar: 'حرج', hi: 'गंभीर' },
  'errors.severity.high':     { en: 'High', fr: 'Élevé', ar: 'مرتفع', hi: 'उच्च' },
  'errors.severity.medium':   { en: 'Medium', fr: 'Moyen', ar: 'متوسط', hi: 'मध्यम' },

  // ── feedback ─────────────────────────────────────────────────────────────
  'feedback.thanksPositive': { en: 'Great! Glad I could help. 😊', fr: 'Parfait ! Ravi d’avoir pu aider. 😊', ar: 'رائع! سعيد بأنني استطعت المساعدة. 😊', hi: 'बढ़िया! खुशी है कि मैं मदद कर सका। 😊' },
  'feedback.sorryNegative':  { en: 'I’m sorry the experience wasn’t helpful.', fr: 'Je suis désolé que cela n’ait pas été utile.', ar: 'يؤسفني أن التجربة لم تكن مفيدة.', hi: 'खेद है कि यह अनुभव सहायक नहीं रहा।' },

  // ── voice input ──────────────────────────────────────────────────────────
  'voice.start':        { en: 'Start voice input', fr: 'Démarrer la saisie vocale', ar: 'بدء الإدخال الصوتي', hi: 'वॉइस इनपुट शुरू करें' },
  'voice.stop':         { en: 'Stop recording', fr: 'Arrêter l’enregistrement', ar: 'إيقاف التسجيل', hi: 'रिकॉर्डिंग रोकें' },
  'voice.transcribing': { en: 'Transcribing…', fr: 'Transcription…', ar: 'جارٍ التفريغ…', hi: 'ट्रांसक्राइब हो रहा है…' },
  'voice.stopTranscribing': { en: 'Stop transcribing', fr: 'Arrêter la transcription', ar: 'إيقاف التفريغ', hi: 'ट्रांसक्रिप्शन रोकें' },
  'voice.speakNow':        { en: 'Speak now…', fr: 'Parlez maintenant…', ar: 'تحدّث الآن…', hi: 'अब बोलें…' },
}
