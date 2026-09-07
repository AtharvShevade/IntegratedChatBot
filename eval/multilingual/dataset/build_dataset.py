"""Builds the frozen parallel query corpus.

The four language sets live here as one aligned table rather than four separate
files so that alignment is structural and cannot drift: every case has the same
id, category and expected_tier in every language, and a missing translation is
a build error rather than a silently short run.

PROVENANCE, which matters for how metric 1 is read: the non-English queries are
authored, not produced by any candidate model. Generating them with the model
under test would mean scoring that model against its own output -- it would
translate its own phrasing back perfectly and look far better than it is.

They have NOT yet been reviewed by native speakers. Until they are, treat the
translation-quality score as indicative and the routing/preservation scores --
which do not depend on the input being idiomatic -- as the load-bearing
numbers. Native review is a prerequisite for a final PASS verdict.

Entity names (RAQ, DBR01, DPSS09, CIMS_ROR, Finance) are deliberately left in
Latin script in every language, because that is how a real user types them.

Run:  python -m eval.multilingual.dataset.build_dataset
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (id, category, expected_tier, {lang: text})
#
# expected_tier records which routing layer the English query is expected to
# land on, so the report can show whether translation pushes queries off the
# deterministic fast paths and onto the slow LLM fallback -- a latency and
# accuracy risk that an intent-only comparison would hide.
#   regex   - keyword/fuzzy fast path (agent/__init__.py:378-449)
#   db_qa   - XML Q&A taxonomy (db_qa/new_intent_classifier.py)
#   sql     - NL->SQL agent
#   llm     - LLM intent extraction fallback
#   conv    - conversational short-circuit
CASES: list[tuple[str, str, str, dict[str, str]]] = [
    # ---------------------------------------------------------------- status
    ("st01", "status", "regex", {
        "en": "what is the status of RAQ",
        "fr": "quel est le statut de RAQ",
        "ar": "ما هي حالة RAQ",
        "hi": "RAQ की स्थिति क्या है",
    }),
    ("st02", "status", "regex", {
        "en": "whats the status of my raq report",
        "fr": "quel est le statut de mon rapport raq",
        "ar": "ما حالة تقرير raq الخاص بي",
        "hi": "मेरी raq रिपोर्ट की स्थिति क्या है",
    }),
    ("st03", "status", "regex", {
        "en": "check status for cims filing",
        "fr": "vérifier le statut du dépôt cims",
        "ar": "تحقق من حالة إيداع cims",
        "hi": "cims फाइलिंग की स्थिति जांचें",
    }),
    ("st04", "status", "regex", {
        "en": "has DPSS09 been generated yet",
        "fr": "est-ce que DPSS09 a déjà été généré",
        "ar": "هل تم إنشاء DPSS09 بعد",
        "hi": "क्या DPSS09 अभी तक जनरेट हुआ है",
    }),
    ("st05", "status", "regex", {
        "en": "is CIMS_ROR overdue",
        "fr": "est-ce que CIMS_ROR est en retard",
        "ar": "هل CIMS_ROR متأخر عن موعده",
        "hi": "क्या CIMS_ROR की समय सीमा निकल चुकी है",
    }),
    ("st06", "status", "regex", {
        "en": "give me a status update on all my reports",
        "fr": "donne-moi une mise à jour du statut de tous mes rapports",
        "ar": "أعطني تحديثًا لحالة جميع تقاريري",
        "hi": "मेरी सभी रिपोर्ट्स की स्थिति का अपडेट दें",
    }),
    ("st07", "status", "regex", {
        "en": "check if RAQ generation succeeded",
        "fr": "vérifie si la génération de RAQ a réussi",
        "ar": "تحقق مما إذا كان إنشاء RAQ قد نجح",
        "hi": "जांचें कि क्या RAQ जनरेशन सफल रहा",
    }),
    ("st08", "status", "regex", {
        "en": "what is the status of my submission ID 1",
        "fr": "quel est le statut de ma soumission ID 1",
        "ar": "ما هي حالة الإرسال الخاص بي ID 1",
        "hi": "मेरे सबमिशन ID 1 की स्थिति क्या है",
    }),

    # -------------------------------------------------------------- generate
    ("gn01", "generate", "regex", {
        "en": "generate the DBR01 report for last quarter end",
        "fr": "génère le rapport DBR01 pour la fin du trimestre dernier",
        "ar": "أنشئ تقرير DBR01 لنهاية الربع الماضي",
        "hi": "पिछली तिमाही के अंत के लिए DBR01 रिपोर्ट जनरेट करें",
    }),
    ("gn02", "generate", "regex", {
        "en": "create a new instance of RAQ for 31st march 2025",
        "fr": "crée une nouvelle instance de RAQ pour le 31 mars 2025",
        "ar": "أنشئ نسخة جديدة من RAQ بتاريخ 31 مارس 2025",
        "hi": "31 मार्च 2025 के लिए RAQ का नया इंस्टेंस बनाएं",
    }),
    ("gn03", "generate", "regex", {
        "en": "kick off CIMS_ROR for today",
        "fr": "lance CIMS_ROR pour aujourd'hui",
        "ar": "ابدأ CIMS_ROR لهذا اليوم",
        "hi": "आज के लिए CIMS_ROR शुरू करें",
    }),
    ("gn04", "generate", "regex", {
        "en": "run raq now",
        "fr": "exécute raq maintenant",
        "ar": "شغّل raq الآن",
        "hi": "raq अभी चलाएं",
    }),
    ("gn05", "generate", "regex", {
        "en": "can you generate raq for last friday",
        "fr": "peux-tu générer raq pour vendredi dernier",
        "ar": "هل يمكنك إنشاء raq ليوم الجمعة الماضي",
        "hi": "क्या आप पिछले शुक्रवार के लिए raq जनरेट कर सकते हैं",
    }),
    ("gn06", "generate", "regex", {
        "en": "generate dbr01 for q1",
        "fr": "génère dbr01 pour le premier trimestre",
        "ar": "أنشئ dbr01 للربع الأول",
        "hi": "पहली तिमाही के लिए dbr01 जनरेट करें",
    }),
    ("gn07", "generate", "regex", {
        "en": "create instance for the report ending 31-12-2025",
        "fr": "crée une instance pour le rapport se terminant le 31-12-2025",
        "ar": "أنشئ نسخة للتقرير المنتهي في 31-12-2025",
        "hi": "31-12-2025 को समाप्त होने वाली रिपोर्ट के लिए इंस्टेंस बनाएं",
    }),

    # -------------------------------------------------------------- schedule
    ("sc01", "schedule", "regex", {
        "en": "schedule DBR01 to run every Monday at 9am",
        "fr": "planifie DBR01 pour qu'il s'exécute chaque lundi à 9h",
        "ar": "جدول DBR01 للتشغيل كل يوم اثنين في الساعة 9 صباحًا",
        "hi": "DBR01 को हर सोमवार सुबह 9 बजे चलाने के लिए शेड्यूल करें",
    }),
    ("sc02", "schedule", "regex", {
        "en": "set up RAQ for next friday at 5:30 pm",
        "fr": "configure RAQ pour vendredi prochain à 17h30",
        "ar": "اضبط RAQ ليوم الجمعة القادم الساعة 5:30 مساءً",
        "hi": "अगले शुक्रवार शाम 5:30 बजे के लिए RAQ सेट करें",
    }),
    ("sc03", "schedule", "regex", {
        "en": "schedule cims filing for the end of this month",
        "fr": "planifie le dépôt cims pour la fin de ce mois",
        "ar": "جدول إيداع cims لنهاية هذا الشهر",
        "hi": "इस महीने के अंत के लिए cims फाइलिंग शेड्यूल करें",
    }),
    ("sc04", "schedule", "regex", {
        "en": "schedule cims for 15th of next month at noon",
        "fr": "planifie cims pour le 15 du mois prochain à midi",
        "ar": "جدول cims ليوم 15 من الشهر القادم عند الظهر",
        "hi": "अगले महीने की 15 तारीख को दोपहर के लिए cims शेड्यूल करें",
    }),
    ("sc05", "schedule", "regex", {
        "en": "schedule the depositor report for next business day",
        "fr": "planifie le rapport des déposants pour le prochain jour ouvrable",
        "ar": "جدول تقرير المودعين ليوم العمل التالي",
        "hi": "अगले कार्य दिवस के लिए डिपॉजिटर रिपोर्ट शेड्यूल करें",
    }),
    ("sc06", "schedule", "regex", {
        "en": "remind me to generate RAQ 2 days before due date",
        "fr": "rappelle-moi de générer RAQ 2 jours avant la date d'échéance",
        "ar": "ذكرني بإنشاء RAQ قبل يومين من تاريخ الاستحقاق",
        "hi": "नियत तिथि से 2 दिन पहले RAQ जनरेट करने की याद दिलाएं",
    }),

    # --------------------------------------------------------------- compare
    ("cp01", "compare", "regex", {
        "en": "compare cims instances from march and april",
        "fr": "compare les instances cims de mars et avril",
        "ar": "قارن نسخ cims من مارس وأبريل",
        "hi": "मार्च और अप्रैल के cims इंस्टेंस की तुलना करें",
    }),
    ("cp02", "compare", "regex", {
        "en": "show variance between last two RAQ filings",
        "fr": "montre l'écart entre les deux derniers dépôts RAQ",
        "ar": "أظهر الفرق بين آخر إيداعين لـ RAQ",
        "hi": "पिछली दो RAQ फाइलिंग के बीच का अंतर दिखाएं",
    }),
    ("cp03", "compare", "regex", {
        "en": "compare this month vs last month DBR01",
        "fr": "compare DBR01 de ce mois-ci avec celui du mois dernier",
        "ar": "قارن DBR01 لهذا الشهر مع الشهر الماضي",
        "hi": "इस महीने बनाम पिछले महीने के DBR01 की तुलना करें",
    }),
    ("cp04", "compare", "regex", {
        "en": "compare my department with report department",
        "fr": "compare mon département avec le département report",
        "ar": "قارن قسمي مع قسم report",
        "hi": "मेरे विभाग की तुलना report विभाग से करें",
    }),
    ("cp05", "compare", "regex", {
        "en": "what changed between the last two CIMS_ROR instances",
        "fr": "qu'est-ce qui a changé entre les deux dernières instances CIMS_ROR",
        "ar": "ما الذي تغير بين آخر نسختين من CIMS_ROR",
        "hi": "पिछले दो CIMS_ROR इंस्टेंस के बीच क्या बदला",
    }),
    ("cp06", "compare", "regex", {
        "en": "variance analysis for DBR01 between q1 and q2",
        "fr": "analyse des écarts pour DBR01 entre le premier et le deuxième trimestre",
        "ar": "تحليل الفروق لـ DBR01 بين الربع الأول والربع الثاني",
        "hi": "पहली और दूसरी तिमाही के बीच DBR01 के लिए विचरण विश्लेषण",
    }),

    # ----------------------------------------------------------------- db_qa
    ("dq01", "db_qa", "db_qa", {
        "en": "what is my role",
        "fr": "quel est mon rôle",
        "ar": "ما هو دوري",
        "hi": "मेरी भूमिका क्या है",
    }),
    ("dq02", "db_qa", "db_qa", {
        "en": "what department am i in",
        "fr": "dans quel département suis-je",
        "ar": "في أي قسم أنا",
        "hi": "मैं किस विभाग में हूं",
    }),
    ("dq03", "db_qa", "db_qa", {
        "en": "who works in Finance",
        "fr": "qui travaille dans Finance",
        "ar": "من يعمل في Finance",
        "hi": "Finance में कौन काम करता है",
    }),
    ("dq04", "db_qa", "db_qa", {
        "en": "list all departments",
        "fr": "liste tous les départements",
        "ar": "اعرض جميع الأقسام",
        "hi": "सभी विभागों की सूची दें",
    }),
    ("dq05", "db_qa", "db_qa", {
        "en": "how many active users are there",
        "fr": "combien d'utilisateurs actifs y a-t-il",
        "ar": "كم عدد المستخدمين النشطين",
        "hi": "कितने सक्रिय उपयोगकर्ता हैं",
    }),
    ("dq06", "db_qa", "db_qa", {
        "en": "what is my email",
        "fr": "quelle est mon adresse e-mail",
        "ar": "ما هو بريدي الإلكتروني",
        "hi": "मेरा ईमेल क्या है",
    }),
    ("dq07", "db_qa", "db_qa", {
        "en": "when did i last login",
        "fr": "quand me suis-je connecté pour la dernière fois",
        "ar": "متى قمت بتسجيل الدخول آخر مرة",
        "hi": "मैंने आखिरी बार कब लॉगिन किया था",
    }),
    ("dq08", "db_qa", "db_qa", {
        "en": "which returns can i submit",
        "fr": "quelles déclarations puis-je soumettre",
        "ar": "ما هي الإقرارات التي يمكنني تقديمها",
        "hi": "मैं कौन से रिटर्न जमा कर सकता हूं",
    }),
    ("dq09", "db_qa", "db_qa", {
        "en": "what is the reporting frequency of DBR01",
        "fr": "quelle est la fréquence de déclaration de DBR01",
        "ar": "ما هو تكرار إعداد التقارير لـ DBR01",
        "hi": "DBR01 की रिपोर्टिंग आवृत्ति क्या है",
    }),
    ("dq10", "db_qa", "db_qa", {
        "en": "list all non-xbrl returns",
        "fr": "liste toutes les déclarations non-xbrl",
        "ar": "اعرض جميع الإقرارات غير xbrl",
        "hi": "सभी गैर-xbrl रिटर्न की सूची दें",
    }),
    ("dq11", "db_qa", "db_qa", {
        "en": "which departments can submit DPSS09",
        "fr": "quels départements peuvent soumettre DPSS09",
        "ar": "ما هي الأقسام التي يمكنها تقديم DPSS09",
        "hi": "कौन से विभाग DPSS09 जमा कर सकते हैं",
    }),
    ("dq12", "db_qa", "db_qa", {
        "en": "how many roles exist in the system",
        "fr": "combien de rôles existent dans le système",
        "ar": "كم عدد الأدوار الموجودة في النظام",
        "hi": "सिस्टम में कितनी भूमिकाएं मौजूद हैं",
    }),
    ("dq13", "db_qa", "db_qa", {
        "en": "show me all reports filed between 01-01-2025 and 31-03-2025",
        "fr": "montre-moi tous les rapports déposés entre le 01-01-2025 et le 31-03-2025",
        "ar": "أظهر لي جميع التقارير المقدمة بين 01-01-2025 و 31-03-2025",
        "hi": "01-01-2025 और 31-03-2025 के बीच दाखिल की गई सभी रिपोर्ट दिखाएं",
    }),
    ("dq14", "db_qa", "db_qa", {
        "en": "what is the due date for DPSS09",
        "fr": "quelle est la date d'échéance de DPSS09",
        "ar": "ما هو تاريخ استحقاق DPSS09",
        "hi": "DPSS09 की नियत तिथि क्या है",
    }),

    # ------------------------------------------------------------- sql_agent
    ("sq01", "sql_agent", "sql", {
        "en": "show me the total deposits from the domestic branch data",
        "fr": "montre-moi le total des dépôts des données des succursales nationales",
        "ar": "أظهر لي إجمالي الودائع من بيانات الفروع المحلية",
        "hi": "घरेलू शाखा डेटा से कुल जमा राशि दिखाएं",
    }),
    ("sq02", "sql_agent", "sql", {
        "en": "what is the derivative notional principal from ALE domestic",
        "fr": "quel est le principal notionnel des dérivés de ALE domestic",
        "ar": "ما هو المبلغ الاسمي للمشتقات من ALE domestic",
        "hi": "ALE domestic से डेरिवेटिव नोशनल प्रिंसिपल क्या है",
    }),
    ("sq03", "sql_agent", "sql", {
        "en": "show me the NPA data for last quarter",
        "fr": "montre-moi les données NPA du dernier trimestre",
        "ar": "أظهر لي بيانات NPA للربع الأخير",
        "hi": "पिछली तिमाही के लिए NPA डेटा दिखाएं",
    }),
    ("sq04", "sql_agent", "sql", {
        "en": "list the top 10 advances by outstanding amount",
        "fr": "liste les 10 principales avances par montant en cours",
        "ar": "اعرض أعلى 10 سلفيات حسب المبلغ المستحق",
        "hi": "बकाया राशि के अनुसार शीर्ष 10 अग्रिमों की सूची दें",
    }),
    ("sq05", "sql_agent", "sql", {
        "en": "total interest income reported for the quarter ending 31-03-2025",
        "fr": "revenu total d'intérêts déclaré pour le trimestre se terminant le 31-03-2025",
        "ar": "إجمالي دخل الفوائد المُبلغ عنه للربع المنتهي في 31-03-2025",
        "hi": "31-03-2025 को समाप्त तिमाही के लिए रिपोर्ट की गई कुल ब्याज आय",
    }),

    # ----------------------------------------------------- error_explanation
    ("er01", "error_explanation", "llm", {
        "en": "explain the errors in RAQ",
        "fr": "explique les erreurs dans RAQ",
        "ar": "اشرح الأخطاء في RAQ",
        "hi": "RAQ में त्रुटियों की व्याख्या करें",
    }),
    ("er02", "error_explanation", "llm", {
        "en": "why did DBR01 fail validation",
        "fr": "pourquoi DBR01 a-t-il échoué à la validation",
        "ar": "لماذا فشل DBR01 في التحقق من الصحة",
        "hi": "DBR01 सत्यापन में विफल क्यों हुआ",
    }),
    ("er03", "error_explanation", "llm", {
        "en": "show me the formula errors for CIMS_ROR",
        "fr": "montre-moi les erreurs de formule pour CIMS_ROR",
        "ar": "أظهر لي أخطاء الصيغة لـ CIMS_ROR",
        "hi": "CIMS_ROR के लिए फॉर्मूला त्रुटियां दिखाएं",
    }),
    ("er04", "error_explanation", "llm", {
        "en": "what validation errors does DPSS09 have",
        "fr": "quelles erreurs de validation DPSS09 présente-t-il",
        "ar": "ما هي أخطاء التحقق الموجودة في DPSS09",
        "hi": "DPSS09 में कौन सी सत्यापन त्रुटियां हैं",
    }),

    # --------------------------------------------------------- conversational
    ("cv01", "conversational", "conv", {
        "en": "hello",
        "fr": "bonjour",
        "ar": "مرحبا",
        "hi": "नमस्ते",
    }),
    ("cv02", "conversational", "conv", {
        "en": "thank you",
        "fr": "merci",
        "ar": "شكرا لك",
        "hi": "धन्यवाद",
    }),
    ("cv03", "conversational", "conv", {
        "en": "what can you do",
        "fr": "que peux-tu faire",
        "ar": "ماذا يمكنك أن تفعل",
        "hi": "आप क्या कर सकते हैं",
    }),
    ("cv04", "conversational", "conv", {
        "en": "who is the prime minister of India",
        "fr": "qui est le premier ministre de l'Inde",
        "ar": "من هو رئيس وزراء الهند",
        "hi": "भारत के प्रधानमंत्री कौन हैं",
    }),
    ("cv05", "conversational", "conv", {
        "en": "tell me stuff about the system",
        "fr": "dis-moi des choses sur le système",
        "ar": "أخبرني بأشياء عن النظام",
        "hi": "मुझे सिस्टम के बारे में कुछ बताएं",
    }),
    ("cv06", "conversational", "conv", {
        "en": "hey can u tell me abt returns pls",
        "fr": "salut peux-tu me parler des déclarations stp",
        "ar": "مرحبا هل يمكنك إخباري عن الإقرارات من فضلك",
        "hi": "अरे क्या आप मुझे रिटर्न के बारे में बता सकते हैं प्लीज",
    }),
]

# Multi-turn cases. reply_mode "numeric" is the language-neutral path and is
# the real signal; "name" is expected to fail for every non-English language
# because the staged matcher at agent/__init__.py:1119-1123 is an ASCII
# substring test against English report names. Both are run so the report can
# separate a model problem from an architecture problem.
MULTI_TURN: list[dict] = [
    {
        "id": "mt01",
        "category": "multi_turn",
        "expected_tier": "regex",
        "reply_mode": "numeric",
        "turns": [
            {"en": "whats the status of my raq report",
             "fr": "quel est le statut de mon rapport raq",
             "ar": "ما حالة تقرير raq الخاص بي",
             "hi": "मेरी raq रिपोर्ट की स्थिति क्या है"},
            {"en": "2", "fr": "2", "ar": "2", "hi": "2"},
        ],
    },
    {
        "id": "mt02",
        "category": "multi_turn",
        "expected_tier": "regex",
        "reply_mode": "numeric",
        "turns": [
            {"en": "check status for cims filing",
             "fr": "vérifier le statut du dépôt cims",
             "ar": "تحقق من حالة إيداع cims",
             "hi": "cims फाइलिंग की स्थिति जांचें"},
            {"en": "1", "fr": "1", "ar": "1", "hi": "1"},
        ],
    },
    {
        "id": "mt03",
        "category": "multi_turn",
        "expected_tier": "regex",
        "reply_mode": "name",
        # Turn 2 is filled in at run time from the previous turn's options[],
        # translated into the target language -- exactly what a real user would
        # do when shown a localised option list.
        "turns": [
            {"en": "whats the status of my raq report",
             "fr": "quel est le statut de mon rapport raq",
             "ar": "ما حالة تقرير raq الخاص بي",
             "hi": "मेरी raq रिपोर्ट की स्थिति क्या है"},
            {"__from_options__": 0},
        ],
    },
    {
        "id": "mt04",
        "category": "multi_turn",
        "expected_tier": "regex",
        "reply_mode": "numeric",
        "turns": [
            {"en": "generate the DBR01 report for last quarter end",
             "fr": "génère le rapport DBR01 pour la fin du trimestre dernier",
             "ar": "أنشئ تقرير DBR01 لنهاية الربع الماضي",
             "hi": "पिछली तिमाही के अंत के लिए DBR01 रिपोर्ट जनरेट करें"},
            {"en": "1", "fr": "1", "ar": "1", "hi": "1"},
        ],
    },
]

LANGS = ("en", "fr", "ar", "hi")


def build() -> dict[str, int]:
    counts: dict[str, int] = {}
    for lang in LANGS:
        rows = []
        for case_id, category, tier, texts in CASES:
            if lang not in texts:
                raise ValueError(f"case {case_id} has no {lang} text")
            rows.append({
                "id": case_id,
                "lang": lang,
                "category": category,
                "expected_tier": tier,
                "text": texts[lang],
                "text_en": texts["en"],
                "multi_turn": False,
            })
        for case in MULTI_TURN:
            turns = []
            for turn in case["turns"]:
                if "__from_options__" in turn:
                    turns.append({"from_options": turn["__from_options__"]})
                else:
                    if lang not in turn:
                        raise ValueError(f"case {case['id']} turn has no {lang} text")
                    turns.append({"text": turn[lang], "text_en": turn["en"]})
            rows.append({
                "id": case["id"],
                "lang": lang,
                "category": case["category"],
                "expected_tier": case["expected_tier"],
                "reply_mode": case["reply_mode"],
                "multi_turn": True,
                "turns": turns,
            })
        path = HERE / f"queries_{lang}.jsonl"
        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        counts[lang] = len(rows)
    return counts


# A frozen 24-case stratified subset, for when a full 60-case run is too
# expensive to justify against a shared inference endpoint.
#
# Written out as an explicit id list rather than computed by a sampling
# function on purpose: every language, every model and every future re-run must
# score the IDENTICAL cases, or the cross-model comparison this harness exists
# to support is worthless. A seeded sampler would drift the moment the dataset
# gains a case.
#
# Coverage held deliberately: all 9 categories; all 4 multi-turn cases (they
# are the only probe of staged-flow behaviour); at least one case per category
# carrying a report/return name, and several carrying dates or numbers, since
# entity preservation is the hard gate.
SUBSET_24 = [
    "st01", "st03", "st05",              # status
    "gn01", "gn03", "gn07",              # generate (gn07 carries 31-12-2025)
    "sc01", "sc04",                      # schedule (times: 9am, noon)
    "cp01", "cp03",                      # compare
    "dq01", "dq04", "dq09", "dq13",      # db_qa (dq13 carries two dates)
    "sq01", "sq05",                      # sql_agent (sq05 carries 31-03-2025)
    "er01", "er03",                      # error explanation
    "cv01", "cv04",                      # conversational (in-scope, out-of-scope)
    "mt01", "mt02", "mt03", "mt04",      # multi-turn (3 numeric, 1 name)
]


# A 5-case screening suite, run across fr/ar/hi = 15 queries per model.
#
# Purpose is different from SUBSET_24: this is a cheap go/no-go filter to decide
# which models deserve a full evaluation at all, not a measurement of one. Five
# cases cannot produce a confident routing-fidelity percentage, and the report
# says so -- what it CAN do is separate a model that mangles report codes or
# takes two minutes a call from one that does not.
#
# Every id is drawn from SUBSET_24 on purpose, so the existing 3x English
# baseline already covers all of them and screening needs no re-baselining.
#
# One case per requested dimension:
SCREEN_5 = [
    "cv01",   # 1. simple / general        -- "hello"; also the cheapest latency probe
    "st01",   # 2. report / routing        -- "what is the status of RAQ" -> disambiguation
    "dq09",   # 3. regulatory entity       -- reporting frequency of DBR01
    "dq13",   # 4. numbers / dates / units -- reports filed between 01-01-2025 and 31-03-2025
    "cp03",   # 5. complex / ambiguous     -- "compare this month vs last month DBR01"
]


# Cases whose ENGLISH baseline is itself wrong, so they cannot fairly score a
# translation. Kept in the suite -- they are informative -- but excluded from
# headline rates and reported separately, the same treatment as a case the
# pipeline cannot reproduce.
#
# Discovered during screening, not assumed up front.
DEGENERATE_BASELINE = {
    "cp03": (
        "The English pipeline mis-parses 'compare this month vs last month DBR01': "
        "it takes the word 'this' as a report name and offers IRS / Phising / "
        "FMRD10_Hedg_Comm_Price_Freight_Risk_Ove as candidates, ignoring DBR01. "
        "Reproduces identically across all 3 baseline runs, so it is a "
        "deterministic pipeline bug rather than noise. A model that renders the "
        "query as 'compare DBR01 for this month with last month' AVOIDS the bug "
        "and resolves DBR01 correctly -- scoring that as a routing miss would "
        "penalise the better translation."
    ),
}


def load(lang: str, subset: bool = False, screen: bool = False) -> list[dict]:
    path = HERE / f"queries_{lang}.jsonl"
    with open(path, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    if screen:
        wanted = set(SCREEN_5)
        selected = [row for row in rows if row["id"] in wanted]
        missing = wanted - {row["id"] for row in selected}
        if missing:
            raise ValueError(f"SCREEN_5 references unknown case ids: {sorted(missing)}")
        return selected
    if not subset:
        return rows
    wanted = set(SUBSET_24)
    selected = [row for row in rows if row["id"] in wanted]
    missing = wanted - {row["id"] for row in selected}
    if missing:
        raise ValueError(f"SUBSET_24 references unknown case ids: {sorted(missing)}")
    return selected


if __name__ == "__main__":
    for lang, n in build().items():
        print(f"queries_{lang}.jsonl: {n} cases")
