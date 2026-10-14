var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// src/App.6.0.css
var require_App_6_0 = __commonJS({
  "src/App.6.0.css"() {
  }
});

// src/App.5.5.css
var require_App_5_5 = __commonJS({
  "src/App.5.5.css"() {
  }
});

// src/App.jsx
import { useState as useState4, useRef as useRef5, useEffect as useEffect5 } from "react";

// src/components/ChatWindow.jsx
import { useEffect as useEffect3, useRef as useRef3 } from "react";

// src/components/MessageBubble.jsx
import React, { useState as useState2, useMemo as useMemo2, useRef as useRef2, useEffect as useEffect2, useCallback as useCallback2 } from "react";
import ReactMarkdown from "react-markdown";

// src/i18n.ui.js
var UI = {
  // ── common: shared across every surface, defined once ────────────────────
  "common.cancel": { en: "Cancel", fr: "Annuler", ar: "\u0625\u0644\u063A\u0627\u0621", hi: "\u0930\u0926\u094D\u0926 \u0915\u0930\u0947\u0902" },
  "common.close": { en: "Close", fr: "Fermer", ar: "\u0625\u063A\u0644\u0627\u0642", hi: "\u092C\u0902\u0926 \u0915\u0930\u0947\u0902" },
  "common.save": { en: "Save", fr: "Enregistrer", ar: "\u062D\u0641\u0638", hi: "\u0938\u0939\u0947\u091C\u0947\u0902" },
  "common.back": { en: "Back", fr: "Retour", ar: "\u0631\u062C\u0648\u0639", hi: "\u0935\u093E\u092A\u0938" },
  "common.submit": { en: "Submit", fr: "Envoyer", ar: "\u0625\u0631\u0633\u0627\u0644", hi: "\u0938\u092C\u092E\u093F\u091F \u0915\u0930\u0947\u0902" },
  "common.search": { en: "Search", fr: "Rechercher", ar: "\u0628\u062D\u062B", hi: "\u0916\u094B\u091C\u0947\u0902" },
  "common.filter": { en: "Filter", fr: "Filtrer", ar: "\u062A\u0635\u0641\u064A\u0629", hi: "\u092B\u093C\u093F\u0932\u094D\u091F\u0930" },
  "common.export": { en: "Export", fr: "Exporter", ar: "\u062A\u0635\u062F\u064A\u0631", hi: "\u0928\u093F\u0930\u094D\u092F\u093E\u0924" },
  "common.download": { en: "Download", fr: "T\xE9l\xE9charger", ar: "\u062A\u0646\u0632\u064A\u0644", hi: "\u0921\u093E\u0909\u0928\u0932\u094B\u0921" },
  "common.refresh": { en: "Refresh", fr: "Actualiser", ar: "\u062A\u062D\u062F\u064A\u062B", hi: "\u0930\u093F\u092B\u093C\u094D\u0930\u0947\u0936" },
  "common.status": { en: "Status", fr: "Statut", ar: "\u0627\u0644\u062D\u0627\u0644\u0629", hi: "\u0938\u094D\u0925\u093F\u0924\u093F" },
  "common.date": { en: "Date", fr: "Date", ar: "\u0627\u0644\u062A\u0627\u0631\u064A\u062E", hi: "\u0924\u093F\u0925\u093F" },
  "common.name": { en: "Name", fr: "Nom", ar: "\u0627\u0644\u0627\u0633\u0645", hi: "\u0928\u093E\u092E" },
  "common.actions": { en: "Actions", fr: "Actions", ar: "\u0627\u0644\u0625\u062C\u0631\u0627\u0621\u0627\u062A", hi: "\u0915\u094D\u0930\u093F\u092F\u093E\u090F\u0901" },
  "common.all": { en: "All", fr: "Tout", ar: "\u0627\u0644\u0643\u0644", hi: "\u0938\u092D\u0940" },
  "common.showing": { en: "Showing", fr: "Affichage de", ar: "\u0639\u0631\u0636", hi: "\u0926\u093F\u0916\u093E \u0930\u0939\u0947 \u0939\u0948\u0902" },
  "common.of": { en: "of", fr: "sur", ar: "\u0645\u0646", hi: "\u092E\u0947\u0902 \u0938\u0947" },
  "common.rows": { en: "Rows", fr: "Lignes", ar: "\u0627\u0644\u0635\u0641\u0648\u0641", hi: "\u092A\u0902\u0915\u094D\u0924\u093F\u092F\u093E\u0901" },
  "common.show": { en: "Show", fr: "Afficher", ar: "\u0625\u0638\u0647\u0627\u0631", hi: "\u0926\u093F\u0916\u093E\u090F\u0901" },
  "common.loading": { en: "Loading\u2026", fr: "Chargement\u2026", ar: "\u062C\u0627\u0631\u064D \u0627\u0644\u062A\u062D\u0645\u064A\u0644\u2026", hi: "\u0932\u094B\u0921 \u0939\u094B \u0930\u0939\u093E \u0939\u0948\u2026" },
  "common.generating": { en: "Generating\u2026", fr: "G\xE9n\xE9ration\u2026", ar: "\u062C\u0627\u0631\u064D \u0627\u0644\u0625\u0646\u0634\u0627\u0621\u2026", hi: "\u092C\u0928\u093E\u092F\u093E \u091C\u093E \u0930\u0939\u093E \u0939\u0948\u2026" },
  "common.select": { en: "Select", fr: "S\xE9lectionner", ar: "\u0627\u062E\u062A\u064A\u0627\u0631", hi: "\u091A\u0941\u0928\u0947\u0902" },
  "common.you": { en: "You", fr: "Vous", ar: "\u0623\u0646\u062A", hi: "\u0906\u092A" },
  "common.notAvailable": { en: "N/A", fr: "S.O.", ar: "\u063A\u064A\u0631 \u0645\u062A\u0627\u062D", hi: "\u0932\u093E\u0917\u0942 \u0928\u0939\u0940\u0902" },
  "comparativeAnalysis.extreme": { en: "Extreme", fr: "Extr\xEAme", ar: "\u0645\u062A\u0637\u0631\u0641", hi: "\u0905\u0924\u094D\u092F\u0927\u093F\u0915" },
  "common.clearFilters": { en: "Clear filters", fr: "Effacer les filtres", ar: "\u0645\u0633\u062D \u0639\u0648\u0627\u0645\u0644 \u0627\u0644\u062A\u0635\u0641\u064A\u0629", hi: "\u092B\u093C\u093F\u0932\u094D\u091F\u0930 \u0938\u093E\u092B\u093C \u0915\u0930\u0947\u0902" },
  // ── status: closed set, mirrors report_lookup._STATUS_LABELS ─────────────
  // The backend VALUE is unchanged; only these display labels are localized.
  "status.approvalPending": { en: "Approval Pending", fr: "En attente d\u2019approbation", ar: "\u0641\u064A \u0627\u0646\u062A\u0638\u0627\u0631 \u0627\u0644\u0645\u0648\u0627\u0641\u0642\u0629", hi: "\u0905\u0928\u0941\u092E\u094B\u0926\u0928 \u0932\u0902\u092C\u093F\u0924" },
  "status.approved": { en: "Approved", fr: "Approuv\xE9", ar: "\u0645\u0639\u062A\u0645\u062F", hi: "\u0905\u0928\u0941\u092E\u094B\u0926\u093F\u0924" },
  "status.failed": { en: "Failed", fr: "\xC9chec", ar: "\u0641\u0634\u0644", hi: "\u0935\u093F\u092B\u0932" },
  "status.inProcess": { en: "In Process", fr: "En cours", ar: "\u0642\u064A\u062F \u0627\u0644\u0645\u0639\u0627\u0644\u062C\u0629", hi: "\u092A\u094D\u0930\u0915\u094D\u0930\u093F\u092F\u093E\u0927\u0940\u0928" },
  "status.inQueue": { en: "In Queue", fr: "En file d\u2019attente", ar: "\u0641\u064A \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0627\u0646\u062A\u0638\u0627\u0631", hi: "\u0915\u0924\u093E\u0930 \u092E\u0947\u0902" },
  "status.unknown": { en: "Unknown", fr: "Inconnu", ar: "\u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641", hi: "\u0905\u091C\u094D\u091E\u093E\u0924" },
  "status.completed": { en: "Completed", fr: "Termin\xE9", ar: "\u0645\u0643\u062A\u0645\u0644", hi: "\u092A\u0942\u0930\u094D\u0923" },
  // ── comparativeAnalysis: variance dashboard, table and chart modal ───────
  "comparativeAnalysis.title": { en: "Variance Visualisation", fr: "Visualisation des \xE9carts", ar: "\u0639\u0631\u0636 \u0627\u0644\u0641\u0631\u0648\u0642\u0627\u062A", hi: "\u092D\u093F\u0928\u094D\u0928\u0924\u093E \u0935\u093F\u091C\u093C\u0941\u0905\u0932\u093E\u0907\u091C\u093C\u0947\u0936\u0928" },
  "comparativeAnalysis.chartTitle": { en: "Variance Chart", fr: "Graphique des \xE9carts", ar: "\u0645\u062E\u0637\u0637 \u0627\u0644\u0641\u0631\u0648\u0642\u0627\u062A", hi: "\u092D\u093F\u0928\u094D\u0928\u0924\u093E \u091A\u093E\u0930\u094D\u091F" },
  "comparativeAnalysis.aiAnalysis": { en: "AI Analysis", fr: "Analyse IA", ar: "\u062A\u062D\u0644\u064A\u0644 \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064A", hi: "AI \u0935\u093F\u0936\u094D\u0932\u0947\u0937\u0923" },
  "comparativeAnalysis.visualize": { en: "Visualize", fr: "Visualiser", ar: "\u0639\u0631\u0636 \u0628\u064A\u0627\u0646\u064A", hi: "\u0935\u093F\u091C\u093C\u0941\u0905\u0932\u093E\u0907\u091C\u093C \u0915\u0930\u0947\u0902" },
  "comparativeAnalysis.openChart": { en: "Open chart visualisation", fr: "Ouvrir la visualisation graphique", ar: "\u0641\u062A\u062D \u0627\u0644\u0639\u0631\u0636 \u0627\u0644\u0628\u064A\u0627\u0646\u064A", hi: "\u091A\u093E\u0930\u094D\u091F \u0935\u093F\u091C\u093C\u0941\u0905\u0932\u093E\u0907\u091C\u093C\u0947\u0936\u0928 \u0916\u094B\u0932\u0947\u0902" },
  "comparativeAnalysis.closeChart": { en: "Close chart", fr: "Fermer le graphique", ar: "\u0625\u063A\u0644\u0627\u0642 \u0627\u0644\u0645\u062E\u0637\u0637", hi: "\u091A\u093E\u0930\u094D\u091F \u092C\u0902\u0926 \u0915\u0930\u0947\u0902" },
  "comparativeAnalysis.stopAnalysis": { en: "Stop generating the AI analysis", fr: "Arr\xEAter la g\xE9n\xE9ration de l\u2019analyse IA", ar: "\u0625\u064A\u0642\u0627\u0641 \u0625\u0646\u0634\u0627\u0621 \u062A\u062D\u0644\u064A\u0644 \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064A", hi: "AI \u0935\u093F\u0936\u094D\u0932\u0947\u0937\u0923 \u092C\u0928\u093E\u0928\u093E \u0930\u094B\u0915\u0947\u0902" },
  "comparativeAnalysis.compareInstances": { en: "Compare Instances", fr: "Comparer les instances", ar: "\u0645\u0642\u0627\u0631\u0646\u0629 \u0627\u0644\u0646\u0633\u062E", hi: "\u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 \u0915\u0940 \u0924\u0941\u0932\u0928\u093E \u0915\u0930\u0947\u0902" },
  "comparativeAnalysis.instance1": { en: "Instance 1", fr: "Instance 1", ar: "\u0627\u0644\u0646\u0633\u062E\u0629 1", hi: "\u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 1" },
  "comparativeAnalysis.instance2": { en: "Instance 2", fr: "Instance 2", ar: "\u0627\u0644\u0646\u0633\u062E\u0629 2", hi: "\u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 2" },
  // Table column headers. The COLUMN KEY (concept / val_a / val_b / diff /
  // pct) is unchanged — sorting and the API contract still use it. The
  // val_a / val_b headers are the INSTANCE LABELS and stay as data.
  "comparativeAnalysis.columns.concept": { en: "Concept", fr: "Concept", ar: "\u0627\u0644\u0645\u0641\u0647\u0648\u0645", hi: "\u0905\u0935\u0927\u093E\u0930\u0923\u093E" },
  "comparativeAnalysis.columns.diff": { en: "Diff", fr: "\xC9cart", ar: "\u0627\u0644\u0641\u0631\u0642", hi: "\u0905\u0902\u0924\u0930" },
  "comparativeAnalysis.columns.pctChange": { en: "% Chg", fr: "% Var.", ar: "% \u0627\u0644\u062A\u063A\u064A\u0651\u0631", hi: "% \u092A\u0930\u093F\u0935\u0930\u094D\u0924\u0928" },
  "comparativeAnalysis.searchConcept": { en: "Search concept\u2026", fr: "Rechercher un concept\u2026", ar: "\u0627\u0628\u062D\u062B \u0639\u0646 \u0645\u0641\u0647\u0648\u0645\u2026", hi: "\u0905\u0935\u0927\u093E\u0930\u0923\u093E \u0916\u094B\u091C\u0947\u0902\u2026" },
  "comparativeAnalysis.searchConceptName": { en: "Search concept name\u2026", fr: "Rechercher un nom de concept\u2026", ar: "\u0627\u0628\u062D\u062B \u0639\u0646 \u0627\u0633\u0645 \u0645\u0641\u0647\u0648\u0645\u2026", hi: "\u0905\u0935\u0927\u093E\u0930\u0923\u093E \u0915\u093E \u0928\u093E\u092E \u0916\u094B\u091C\u0947\u0902\u2026" },
  "comparativeAnalysis.filterTooltip": { en: "Filter the table by concept name", fr: "Filtrer le tableau par nom de concept", ar: "\u062A\u0635\u0641\u064A\u0629 \u0627\u0644\u062C\u062F\u0648\u0644 \u062D\u0633\u0628 \u0627\u0633\u0645 \u0627\u0644\u0645\u0641\u0647\u0648\u0645", hi: "\u0905\u0935\u0927\u093E\u0930\u0923\u093E \u0928\u093E\u092E \u0938\u0947 \u0924\u093E\u0932\u093F\u0915\u093E \u092B\u093C\u093F\u0932\u094D\u091F\u0930 \u0915\u0930\u0947\u0902" },
  "comparativeAnalysis.filterChartTooltip": { en: "Filter the chart by concept name", fr: "Filtrer le graphique par nom de concept", ar: "\u062A\u0635\u0641\u064A\u0629 \u0627\u0644\u0645\u062E\u0637\u0637 \u062D\u0633\u0628 \u0627\u0633\u0645 \u0627\u0644\u0645\u0641\u0647\u0648\u0645", hi: "\u0905\u0935\u0927\u093E\u0930\u0923\u093E \u0928\u093E\u092E \u0938\u0947 \u091A\u093E\u0930\u094D\u091F \u092B\u093C\u093F\u0932\u094D\u091F\u0930 \u0915\u0930\u0947\u0902" },
  "comparativeAnalysis.filterNoteTable": { en: "Filters which facts the table lists. Does not change the comparison.", fr: "Filtre les faits list\xE9s dans le tableau. Ne modifie pas la comparaison.", ar: "\u064A\u0635\u0641\u0651\u064A \u0627\u0644\u062D\u0642\u0627\u0626\u0642 \u0627\u0644\u0645\u0639\u0631\u0648\u0636\u0629 \u0641\u064A \u0627\u0644\u062C\u062F\u0648\u0644. \u0644\u0627 \u064A\u063A\u064A\u0651\u0631 \u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0629.", hi: "\u0924\u093E\u0932\u093F\u0915\u093E \u092E\u0947\u0902 \u0926\u093F\u0916\u093E\u090F \u0917\u090F \u0924\u0925\u094D\u092F\u094B\u0902 \u0915\u094B \u092B\u093C\u093F\u0932\u094D\u091F\u0930 \u0915\u0930\u0924\u093E \u0939\u0948\u0964 \u0924\u0941\u0932\u0928\u093E \u0928\u0939\u0940\u0902 \u092C\u0926\u0932\u0924\u093E\u0964" },
  "comparativeAnalysis.filterNoteChart": { en: "Filters which facts the chart draws. Does not change the comparison.", fr: "Filtre les faits trac\xE9s dans le graphique. Ne modifie pas la comparaison.", ar: "\u064A\u0635\u0641\u0651\u064A \u0627\u0644\u062D\u0642\u0627\u0626\u0642 \u0627\u0644\u0645\u0631\u0633\u0648\u0645\u0629 \u0641\u064A \u0627\u0644\u0645\u062E\u0637\u0637. \u0644\u0627 \u064A\u063A\u064A\u0651\u0631 \u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0629.", hi: "\u091A\u093E\u0930\u094D\u091F \u092E\u0947\u0902 \u092C\u0928\u093E\u090F \u0917\u090F \u0924\u0925\u094D\u092F\u094B\u0902 \u0915\u094B \u092B\u093C\u093F\u0932\u094D\u091F\u0930 \u0915\u0930\u0924\u093E \u0939\u0948\u0964 \u0924\u0941\u0932\u0928\u093E \u0928\u0939\u0940\u0902 \u092C\u0926\u0932\u0924\u093E\u0964" },
  "comparativeAnalysis.rowsNoteTable": { en: "How many rows to list. Display only \u2014 the comparison keeps every concept.", fr: "Nombre de lignes \xE0 lister. Affichage seulement \u2014 la comparaison conserve tous les concepts.", ar: "\u0639\u062F\u062F \u0627\u0644\u0635\u0641\u0648\u0641 \u0627\u0644\u0645\u0639\u0631\u0648\u0636\u0629. \u0644\u0644\u0639\u0631\u0636 \u0641\u0642\u0637 \u2014 \u062A\u062D\u062A\u0641\u0638 \u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0629 \u0628\u0643\u0644 \u0627\u0644\u0645\u0641\u0627\u0647\u064A\u0645.", hi: "\u0915\u093F\u0924\u0928\u0940 \u092A\u0902\u0915\u094D\u0924\u093F\u092F\u093E\u0901 \u0926\u093F\u0916\u093E\u0928\u0940 \u0939\u0948\u0902\u0964 \u0915\u0947\u0935\u0932 \u092A\u094D\u0930\u0926\u0930\u094D\u0936\u0928 \u2014 \u0924\u0941\u0932\u0928\u093E \u0939\u0930 \u0905\u0935\u0927\u093E\u0930\u0923\u093E \u0930\u0916\u0924\u0940 \u0939\u0948\u0964" },
  "comparativeAnalysis.rowsNoteChart": { en: "How many rows to draw, taken from the top of the current ranking.", fr: "Nombre de lignes \xE0 tracer, prises en haut du classement actuel.", ar: "\u0639\u062F\u062F \u0627\u0644\u0635\u0641\u0648\u0641 \u0627\u0644\u0645\u0631\u0633\u0648\u0645\u0629\u060C \u0645\u0646 \u0623\u0639\u0644\u0649 \u0627\u0644\u062A\u0631\u062A\u064A\u0628 \u0627\u0644\u062D\u0627\u0644\u064A.", hi: "\u0915\u093F\u0924\u0928\u0940 \u092A\u0902\u0915\u094D\u0924\u093F\u092F\u093E\u0901 \u092C\u0928\u093E\u0928\u0940 \u0939\u0948\u0902, \u0935\u0930\u094D\u0924\u092E\u093E\u0928 \u0930\u0948\u0902\u0915\u093F\u0902\u0917 \u0915\u0947 \u0936\u0940\u0930\u094D\u0937 \u0938\u0947\u0964" },
  "comparativeAnalysis.showPctChange": { en: "Show % change per concept", fr: "Afficher la variation en % par concept", ar: "\u0625\u0638\u0647\u0627\u0631 \u0646\u0633\u0628\u0629 \u0627\u0644\u062A\u063A\u064A\u0651\u0631 \u0644\u0643\u0644 \u0645\u0641\u0647\u0648\u0645", hi: "\u092A\u094D\u0930\u0924\u093F \u0905\u0935\u0927\u093E\u0930\u0923\u093E % \u092A\u0930\u093F\u0935\u0930\u094D\u0924\u0928 \u0926\u093F\u0916\u093E\u090F\u0901" },
  "comparativeAnalysis.factsCompared": { en: "Facts compared", fr: "Faits compar\xE9s", ar: "\u0627\u0644\u062D\u0642\u0627\u0626\u0642 \u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0629", hi: "\u0924\u0941\u0932\u0928\u093E \u0915\u093F\u090F \u0917\u090F \u0924\u0925\u094D\u092F" },
  "comparativeAnalysis.comparableFacts": { en: "Comparable Facts", fr: "Faits comparables", ar: "\u0627\u0644\u062D\u0642\u0627\u0626\u0642 \u0627\u0644\u0642\u0627\u0628\u0644\u0629 \u0644\u0644\u0645\u0642\u0627\u0631\u0646\u0629", hi: "\u0924\u0941\u0932\u0928\u0940\u092F \u0924\u0925\u094D\u092F" },
  "comparativeAnalysis.concepts": { en: "Concepts", fr: "Concepts", ar: "\u0627\u0644\u0645\u0641\u0627\u0647\u064A\u0645", hi: "\u0905\u0935\u0927\u093E\u0930\u0923\u093E\u090F\u0901" },
  "comparativeAnalysis.increased": { en: "Increased", fr: "En hausse", ar: "\u0627\u0631\u062A\u0641\u0639", hi: "\u092C\u0922\u093C\u093E" },
  "comparativeAnalysis.decreased": { en: "Decreased", fr: "En baisse", ar: "\u0627\u0646\u062E\u0641\u0636", hi: "\u0918\u091F\u093E" },
  "comparativeAnalysis.unchanged": { en: "Unchanged", fr: "Inchang\xE9", ar: "\u062F\u0648\u0646 \u062A\u063A\u064A\u064A\u0631", hi: "\u0905\u092A\u0930\u093F\u0935\u0930\u094D\u0924\u093F\u0924" },
  "comparativeAnalysis.reversed": { en: "Reversed", fr: "Invers\xE9", ar: "\u0645\u0639\u0643\u0648\u0633", hi: "\u0909\u0932\u091F\u093E" },
  "comparativeAnalysis.noChange": { en: "No Change", fr: "Aucun changement", ar: "\u0644\u0627 \u062A\u063A\u064A\u064A\u0631", hi: "\u0915\u094B\u0908 \u092A\u0930\u093F\u0935\u0930\u094D\u0924\u0928 \u0928\u0939\u0940\u0902" },
  "comparativeAnalysis.current": { en: "Current", fr: "Actuel", ar: "\u0627\u0644\u062D\u0627\u0644\u064A", hi: "\u0935\u0930\u094D\u0924\u092E\u093E\u0928" },
  "comparativeAnalysis.previous": { en: "Previous", fr: "Pr\xE9c\xE9dent", ar: "\u0627\u0644\u0633\u0627\u0628\u0642", hi: "\u092A\u093F\u091B\u0932\u093E" },
  "comparativeAnalysis.importance": { en: "Importance", fr: "Importance", ar: "\u0627\u0644\u0623\u0647\u0645\u064A\u0629", hi: "\u092E\u0939\u0924\u094D\u0935" },
  "comparativeAnalysis.rankedBy": { en: "Ranked by", fr: "Class\xE9 par", ar: "\u0645\u0631\u062A\u0651\u0628 \u062D\u0633\u0628", hi: "\u0915\u094D\u0930\u092E\u092C\u0926\u094D\u0927" },
  "comparativeAnalysis.inTier": { en: "in tier", fr: "dans le niveau", ar: "\u0641\u064A \u0627\u0644\u0645\u0633\u062A\u0648\u0649", hi: "\u0936\u094D\u0930\u0947\u0923\u0940 \u092E\u0947\u0902" },
  "comparativeAnalysis.downloadNote": { en: "Download always exports the full set.", fr: "Le t\xE9l\xE9chargement exporte toujours l\u2019ensemble complet.", ar: "\u064A\u0635\u062F\u0651\u0631 \u0627\u0644\u062A\u0646\u0632\u064A\u0644 \u062F\u0627\u0626\u0645\u064B\u0627 \u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629 \u0627\u0644\u0643\u0627\u0645\u0644\u0629.", hi: "\u0921\u093E\u0909\u0928\u0932\u094B\u0921 \u0939\u092E\u0947\u0936\u093E \u092A\u0942\u0930\u093E \u0938\u0947\u091F \u0928\u093F\u0930\u094D\u092F\u093E\u0924 \u0915\u0930\u0924\u093E \u0939\u0948\u0964" },
  "comparativeAnalysis.noRows": { en: "No rows to display.", fr: "Aucune ligne \xE0 afficher.", ar: "\u0644\u0627 \u062A\u0648\u062C\u062F \u0635\u0641\u0648\u0641 \u0644\u0644\u0639\u0631\u0636.", hi: "\u0926\u093F\u0916\u093E\u0928\u0947 \u0915\u0947 \u0932\u093F\u090F \u0915\u094B\u0908 \u092A\u0902\u0915\u094D\u0924\u093F \u0928\u0939\u0940\u0902\u0964" },
  "comparativeAnalysis.noFactsMatch": { en: "No facts match this filter.", fr: "Aucun fait ne correspond \xE0 ce filtre.", ar: "\u0644\u0627 \u062A\u0648\u062C\u062F \u062D\u0642\u0627\u0626\u0642 \u062A\u0637\u0627\u0628\u0642 \u0647\u0630\u0627 \u0627\u0644\u0641\u0644\u062A\u0631.", hi: "\u0907\u0938 \u092B\u093C\u093F\u0932\u094D\u091F\u0930 \u0938\u0947 \u0915\u094B\u0908 \u0924\u0925\u094D\u092F \u092E\u0947\u0932 \u0928\u0939\u0940\u0902 \u0916\u093E\u0924\u093E\u0964" },
  "comparativeAnalysis.highVariance": { en: "High variance", fr: "\xC9cart \xE9lev\xE9", ar: "\u0641\u0631\u0642 \u0643\u0628\u064A\u0631", hi: "\u0909\u091A\u094D\u091A \u092D\u093F\u0928\u094D\u0928\u0924\u093E" },
  "comparativeAnalysis.bothPeriodsNote": { en: "The fact was reported in both periods \u2014 this is a real comparison, not missing data.", fr: "Le fait a \xE9t\xE9 d\xE9clar\xE9 sur les deux p\xE9riodes \u2014 il s\u2019agit d\u2019une vraie comparaison, pas de donn\xE9es manquantes.", ar: "\u062A\u0645 \u0627\u0644\u0625\u0628\u0644\u0627\u063A \u0639\u0646 \u0627\u0644\u062D\u0642\u064A\u0642\u0629 \u0641\u064A \u0643\u0644\u062A\u0627 \u0627\u0644\u0641\u062A\u0631\u062A\u064A\u0646 \u2014 \u0647\u0630\u0647 \u0645\u0642\u0627\u0631\u0646\u0629 \u062D\u0642\u064A\u0642\u064A\u0629 \u0648\u0644\u064A\u0633\u062A \u0628\u064A\u0627\u0646\u0627\u062A \u0645\u0641\u0642\u0648\u062F\u0629.", hi: "\u092F\u0939 \u0924\u0925\u094D\u092F \u0926\u094B\u0928\u094B\u0902 \u0905\u0935\u0927\u093F\u092F\u094B\u0902 \u092E\u0947\u0902 \u0926\u0930\u094D\u091C \u0915\u093F\u092F\u093E \u0917\u092F\u093E \u2014 \u092F\u0939 \u0935\u093E\u0938\u094D\u0924\u0935\u093F\u0915 \u0924\u0941\u0932\u0928\u093E \u0939\u0948, \u0905\u0928\u0941\u092A\u0932\u092C\u094D\u0927 \u0921\u0947\u091F\u093E \u0928\u0939\u0940\u0902\u0964" },
  "comparativeAnalysis.zeroPreviousNote": { en: "Previous value was 0 \u2014 no % change (reported in both periods)", fr: "La valeur pr\xE9c\xE9dente \xE9tait 0 \u2014 pas de variation en % (d\xE9clar\xE9e sur les deux p\xE9riodes)", ar: "\u0643\u0627\u0646\u062A \u0627\u0644\u0642\u064A\u0645\u0629 \u0627\u0644\u0633\u0627\u0628\u0642\u0629 0 \u2014 \u0644\u0627 \u0646\u0633\u0628\u0629 \u062A\u063A\u064A\u0651\u0631 (\u0645\u064F\u0628\u0644\u063A \u0639\u0646\u0647\u0627 \u0641\u064A \u0643\u0644\u062A\u0627 \u0627\u0644\u0641\u062A\u0631\u062A\u064A\u0646)", hi: "\u092A\u093F\u091B\u0932\u093E \u092E\u093E\u0928 0 \u0925\u093E \u2014 \u0915\u094B\u0908 % \u092A\u0930\u093F\u0935\u0930\u094D\u0924\u0928 \u0928\u0939\u0940\u0902 (\u0926\u094B\u0928\u094B\u0902 \u0905\u0935\u0927\u093F\u092F\u094B\u0902 \u092E\u0947\u0902 \u0926\u0930\u094D\u091C)" },
  // Filter legend shared by the variance table and the chart modal.
  // The FILTER KEY ('all','sig','up','down','reversal','zero') is unchanged.
  "comparativeAnalysis.filters.allDesc": { en: "Every fact present in both periods", fr: "Tous les faits pr\xE9sents sur les deux p\xE9riodes", ar: "\u0643\u0644 \u062D\u0642\u064A\u0642\u0629 \u0645\u0648\u062C\u0648\u062F\u0629 \u0641\u064A \u0643\u0644\u062A\u0627 \u0627\u0644\u0641\u062A\u0631\u062A\u064A\u0646", hi: "\u0926\u094B\u0928\u094B\u0902 \u0905\u0935\u0927\u093F\u092F\u094B\u0902 \u092E\u0947\u0902 \u092E\u094C\u091C\u0942\u0926 \u0939\u0930 \u0924\u0925\u094D\u092F" },
  "comparativeAnalysis.filters.sigDesc": { en: "Facts flagged high-variance by the variance logic", fr: "Faits signal\xE9s \xE0 \xE9cart \xE9lev\xE9 par la logique de variance", ar: "\u0627\u0644\u062D\u0642\u0627\u0626\u0642 \u0627\u0644\u0645\u0635\u0646\u0651\u0641\u0629 \u0639\u0627\u0644\u064A\u0629 \u0627\u0644\u0641\u0631\u0648\u0642 \u0648\u0641\u0642 \u0645\u0646\u0637\u0642 \u0627\u0644\u0641\u0631\u0648\u0642\u0627\u062A", hi: "\u092D\u093F\u0928\u094D\u0928\u0924\u093E \u0924\u0930\u094D\u0915 \u0926\u094D\u0935\u093E\u0930\u093E \u0909\u091A\u094D\u091A-\u092D\u093F\u0928\u094D\u0928\u0924\u093E \u091A\u093F\u0939\u094D\u0928\u093F\u0924 \u0924\u0925\u094D\u092F" },
  "comparativeAnalysis.filters.upDesc": { en: "Current period is higher than the previous period", fr: "La p\xE9riode actuelle est sup\xE9rieure \xE0 la pr\xE9c\xE9dente", ar: "\u0627\u0644\u0641\u062A\u0631\u0629 \u0627\u0644\u062D\u0627\u0644\u064A\u0629 \u0623\u0639\u0644\u0649 \u0645\u0646 \u0627\u0644\u0641\u062A\u0631\u0629 \u0627\u0644\u0633\u0627\u0628\u0642\u0629", hi: "\u0935\u0930\u094D\u0924\u092E\u093E\u0928 \u0905\u0935\u0927\u093F \u092A\u093F\u091B\u0932\u0940 \u0905\u0935\u0927\u093F \u0938\u0947 \u0905\u0927\u093F\u0915 \u0939\u0948" },
  "comparativeAnalysis.filters.downDesc": { en: "Current period is lower than the previous period", fr: "La p\xE9riode actuelle est inf\xE9rieure \xE0 la pr\xE9c\xE9dente", ar: "\u0627\u0644\u0641\u062A\u0631\u0629 \u0627\u0644\u062D\u0627\u0644\u064A\u0629 \u0623\u0642\u0644 \u0645\u0646 \u0627\u0644\u0641\u062A\u0631\u0629 \u0627\u0644\u0633\u0627\u0628\u0642\u0629", hi: "\u0935\u0930\u094D\u0924\u092E\u093E\u0928 \u0905\u0935\u0927\u093F \u092A\u093F\u091B\u0932\u0940 \u0905\u0935\u0927\u093F \u0938\u0947 \u0915\u092E \u0939\u0948" },
  "comparativeAnalysis.filters.reversalDesc": { en: "The value crossed zero \u2014 sign reversal", fr: "La valeur a franchi z\xE9ro \u2014 inversion de signe", ar: "\u062A\u062C\u0627\u0648\u0632\u062A \u0627\u0644\u0642\u064A\u0645\u0629 \u0627\u0644\u0635\u0641\u0631 \u2014 \u0627\u0646\u0639\u0643\u0627\u0633 \u0627\u0644\u0625\u0634\u0627\u0631\u0629", hi: "\u092E\u093E\u0928 \u0936\u0942\u0928\u094D\u092F \u0915\u094B \u092A\u093E\u0930 \u0915\u0930 \u0917\u092F\u093E \u2014 \u091A\u093F\u0939\u094D\u0928 \u0909\u0932\u091F\u093E\u0935" },
  "comparativeAnalysis.filters.zero": { en: "Previous was 0", fr: "Pr\xE9c\xE9dent \xE9tait 0", ar: "\u0627\u0644\u0633\u0627\u0628\u0642 \u0643\u0627\u0646 0", hi: "\u092A\u093F\u091B\u0932\u093E 0 \u0925\u093E" },
  // ── chart controls & legend ──────────────────────────────────────────────
  "comparativeAnalysis.downloadTooltip": { en: "Download a standalone HTML file with all {0} comparable facts", fr: "T\xE9l\xE9charger un fichier HTML autonome contenant les {0} faits comparables", ar: "\u062A\u0646\u0632\u064A\u0644 \u0645\u0644\u0641 HTML \u0645\u0633\u062A\u0642\u0644 \u064A\u062D\u062A\u0648\u064A \u0639\u0644\u0649 \u062C\u0645\u064A\u0639 \u0627\u0644\u062D\u0642\u0627\u0626\u0642 \u0627\u0644\u0642\u0627\u0628\u0644\u0629 \u0644\u0644\u0645\u0642\u0627\u0631\u0646\u0629 \u0627\u0644\u0628\u0627\u0644\u063A\u0629 {0}", hi: "\u0938\u092D\u0940 {0} \u0924\u0941\u0932\u0928\u0940\u092F \u0924\u0925\u094D\u092F\u094B\u0902 \u0935\u093E\u0932\u0940 \u0938\u094D\u0935\u0924\u0902\u0924\u094D\u0930 HTML \u092B\u093C\u093E\u0907\u0932 \u0921\u093E\u0909\u0928\u0932\u094B\u0921 \u0915\u0930\u0947\u0902" },
  "comparativeAnalysis.chartBar": { en: "Bar", fr: "Barres", ar: "\u0623\u0639\u0645\u062F\u0629", hi: "\u092C\u093E\u0930" },
  "comparativeAnalysis.chartLine": { en: "Line", fr: "Courbe", ar: "\u062E\u0637\u064A", hi: "\u0930\u0947\u0916\u093E" },
  "comparativeAnalysis.legendIncrease": { en: "Increase", fr: "Hausse", ar: "\u0632\u064A\u0627\u062F\u0629", hi: "\u0935\u0943\u0926\u094D\u0927\u093F" },
  "comparativeAnalysis.legendDecrease": { en: "Decrease", fr: "Baisse", ar: "\u0627\u0646\u062E\u0641\u0627\u0636", hi: "\u0915\u092E\u0940" },
  "comparativeAnalysis.legendNoChange": { en: "No change", fr: "Aucun changement", ar: "\u0644\u0627 \u062A\u063A\u064A\u064A\u0631", hi: "\u0915\u094B\u0908 \u092A\u0930\u093F\u0935\u0930\u094D\u0924\u0928 \u0928\u0939\u0940\u0902" },
  "comparativeAnalysis.legendReversedOutlined": { en: "Reversed (outlined)", fr: "Invers\xE9 (contour)", ar: "\u0645\u0639\u0643\u0648\u0633 (\u0645\u062D\u062F\u0651\u062F)", hi: "\u0909\u0932\u091F\u093E (\u0930\u0942\u092A\u0930\u0947\u0916\u093E)" },
  "comparativeAnalysis.directionReversed": { en: "Direction reversed", fr: "Sens invers\xE9", ar: "\u0627\u0646\u0639\u0643\u0633 \u0627\u0644\u0627\u062A\u062C\u0627\u0647", hi: "\u0926\u093F\u0936\u093E \u0909\u0932\u091F\u0940" },
  "comparativeAnalysis.veryHigh": { en: "Very High", fr: "Tr\xE8s \xE9lev\xE9", ar: "\u0645\u0631\u062A\u0641\u0639 \u062C\u062F\u064B\u0627", hi: "\u092C\u0939\u0941\u0924 \u0909\u091A\u094D\u091A" },
  // ── ranking controls ─────────────────────────────────────────────────────
  "comparativeAnalysis.rankAbsoluteDiff": { en: "Absolute Diff", fr: "\xC9cart absolu", ar: "\u0627\u0644\u0641\u0631\u0642 \u0627\u0644\u0645\u0637\u0644\u0642", hi: "\u0928\u093F\u0930\u092A\u0947\u0915\u094D\u0937 \u0905\u0902\u0924\u0930" },
  "comparativeAnalysis.rankPctChange": { en: "% Change", fr: "% de variation", ar: "% \u0627\u0644\u062A\u063A\u064A\u0651\u0631", hi: "% \u092A\u0930\u093F\u0935\u0930\u094D\u0924\u0928" },
  "comparativeAnalysis.rankAbsoluteDiffDesc": { en: "Largest absolute difference first. Surfaces the biggest movements in value terms, regardless of how small they are in percentage terms.", fr: "\xC9cart absolu le plus \xE9lev\xE9 en premier. Fait ressortir les plus grands mouvements en valeur, quelle que soit leur faiblesse en pourcentage.", ar: "\u0627\u0644\u0641\u0631\u0642 \u0627\u0644\u0645\u0637\u0644\u0642 \u0627\u0644\u0623\u0643\u0628\u0631 \u0623\u0648\u0644\u064B\u0627. \u064A\u064F\u0628\u0631\u0632 \u0623\u0643\u0628\u0631 \u0627\u0644\u062A\u062D\u0631\u0643\u0627\u062A \u0645\u0646 \u062D\u064A\u062B \u0627\u0644\u0642\u064A\u0645\u0629\u060C \u0645\u0647\u0645\u0627 \u0643\u0627\u0646\u062A \u0635\u063A\u064A\u0631\u0629 \u0628\u0627\u0644\u0646\u0633\u0628\u0629 \u0627\u0644\u0645\u0626\u0648\u064A\u0629.", hi: "\u0938\u092C\u0938\u0947 \u092C\u0921\u093C\u093E \u0928\u093F\u0930\u092A\u0947\u0915\u094D\u0937 \u0905\u0902\u0924\u0930 \u092A\u0939\u0932\u0947\u0964 \u092E\u0942\u0932\u094D\u092F \u0915\u0947 \u0939\u093F\u0938\u093E\u092C \u0938\u0947 \u0938\u092C\u0938\u0947 \u092C\u0921\u093C\u0947 \u092C\u0926\u0932\u093E\u0935 \u0938\u093E\u092E\u0928\u0947 \u0932\u093E\u0924\u093E \u0939\u0948, \u091A\u093E\u0939\u0947 \u092A\u094D\u0930\u0924\u093F\u0936\u0924 \u092E\u0947\u0902 \u0935\u0947 \u0915\u093F\u0924\u0928\u0947 \u092D\u0940 \u091B\u094B\u091F\u0947 \u0939\u094B\u0902\u0964" },
  "comparativeAnalysis.rankPctChangeDesc": { en: "Largest percentage movement first. Surfaces volatility \u2014 a small line that doubled outranks a large line that moved 3%.", fr: "Variation en pourcentage la plus forte en premier. Fait ressortir la volatilit\xE9 \u2014 une petite ligne qui a doubl\xE9 passe devant une grande ligne ayant boug\xE9 de 3 %.", ar: "\u0623\u0643\u0628\u0631 \u062A\u063A\u064A\u0651\u0631 \u0628\u0627\u0644\u0646\u0633\u0628\u0629 \u0627\u0644\u0645\u0626\u0648\u064A\u0629 \u0623\u0648\u0644\u064B\u0627. \u064A\u064F\u0628\u0631\u0632 \u0627\u0644\u062A\u0642\u0644\u0628 \u2014 \u0628\u0646\u062F \u0635\u063A\u064A\u0631 \u062A\u0636\u0627\u0639\u0641 \u064A\u062A\u0642\u062F\u0651\u0645 \u0639\u0644\u0649 \u0628\u0646\u062F \u0643\u0628\u064A\u0631 \u062A\u062D\u0631\u0651\u0643 \u0628\u0646\u0633\u0628\u0629 3%.", hi: "\u0938\u092C\u0938\u0947 \u092C\u0921\u093C\u093E \u092A\u094D\u0930\u0924\u093F\u0936\u0924 \u092C\u0926\u0932\u093E\u0935 \u092A\u0939\u0932\u0947\u0964 \u0905\u0938\u094D\u0925\u093F\u0930\u0924\u093E \u0938\u093E\u092E\u0928\u0947 \u0932\u093E\u0924\u093E \u0939\u0948 \u2014 \u0926\u094B\u0917\u0941\u0928\u0940 \u0939\u0941\u0908 \u091B\u094B\u091F\u0940 \u092A\u0902\u0915\u094D\u0924\u093F 3% \u091A\u0932\u0940 \u092C\u0921\u093C\u0940 \u092A\u0902\u0915\u094D\u0924\u093F \u0938\u0947 \u090A\u092A\u0930 \u0906\u0924\u0940 \u0939\u0948\u0964" },
  "comparativeAnalysis.defaultRanking": { en: "variance priority", fr: "priorit\xE9 de variance", ar: "\u0623\u0648\u0644\u0648\u064A\u0629 \u0627\u0644\u0641\u0631\u0648\u0642\u0627\u062A", hi: "\u092D\u093F\u0928\u094D\u0928\u0924\u093E \u092A\u094D\u0930\u093E\u0925\u092E\u093F\u0915\u0924\u093E" },
  "comparativeAnalysis.tierFilterTooltip": { en: "Filter by regulatory-importance tier from the return\u2019s taxonomy JSON. Display only \u2014 the comparison keeps every concept.", fr: "Filtrer par niveau d\u2019importance r\xE9glementaire issu du JSON de taxonomie du rapport. Affichage seulement \u2014 la comparaison conserve tous les concepts.", ar: "\u0627\u0644\u062A\u0635\u0641\u064A\u0629 \u062D\u0633\u0628 \u0645\u0633\u062A\u0648\u0649 \u0627\u0644\u0623\u0647\u0645\u064A\u0629 \u0627\u0644\u062A\u0646\u0638\u064A\u0645\u064A\u0629 \u0645\u0646 \u0645\u0644\u0641 JSON \u0627\u0644\u062E\u0627\u0635 \u0628\u062A\u0635\u0646\u064A\u0641 \u0627\u0644\u062A\u0642\u0631\u064A\u0631. \u0644\u0644\u0639\u0631\u0636 \u0641\u0642\u0637 \u2014 \u062A\u062D\u062A\u0641\u0638 \u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0629 \u0628\u0643\u0644 \u0627\u0644\u0645\u0641\u0627\u0647\u064A\u0645.", hi: "\u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0915\u0940 \u091F\u0948\u0915\u094D\u0938\u094B\u0928\u0949\u092E\u0940 JSON \u0938\u0947 \u0928\u093F\u092F\u093E\u092E\u0915-\u092E\u0939\u0924\u094D\u0935 \u0936\u094D\u0930\u0947\u0923\u0940 \u0926\u094D\u0935\u093E\u0930\u093E \u092B\u093C\u093F\u0932\u094D\u091F\u0930 \u0915\u0930\u0947\u0902\u0964 \u0915\u0947\u0935\u0932 \u092A\u094D\u0930\u0926\u0930\u094D\u0936\u0928 \u2014 \u0924\u0941\u0932\u0928\u093E \u0939\u0930 \u0905\u0935\u0927\u093E\u0930\u0923\u093E \u0930\u0916\u0924\u0940 \u0939\u0948\u0964" },
  // ── coverage caption: one template per shape, values inserted locally ─────
  "comparativeAnalysis.showingTopOf": { en: "Showing top {0} of {1}", fr: "Affichage des {0} principaux sur {1}", ar: "\u0639\u0631\u0636 \u0623\u0639\u0644\u0649 {0} \u0645\u0646 {1}", hi: "{1} \u092E\u0947\u0902 \u0938\u0947 \u0936\u0940\u0930\u094D\u0937 {0} \u0926\u093F\u0916\u093E \u0930\u0939\u0947 \u0939\u0948\u0902" },
  "comparativeAnalysis.showingAll": { en: "Showing all {0}", fr: "Affichage des {0}", ar: "\u0639\u0631\u0636 \u062C\u0645\u064A\u0639 \u0627\u0644\u0640 {0}", hi: "\u0938\u092D\u0940 {0} \u0926\u093F\u0916\u093E \u0930\u0939\u0947 \u0939\u0948\u0902" },
  "comparativeAnalysis.comparableFacts": { en: "comparable facts", fr: "faits comparables", ar: "\u062D\u0642\u0627\u0626\u0642 \u0642\u0627\u0628\u0644\u0629 \u0644\u0644\u0645\u0642\u0627\u0631\u0646\u0629", hi: "\u0924\u0941\u0932\u0928\u0940\u092F \u0924\u0925\u094D\u092F" },
  "comparativeAnalysis.matchingFacts": { en: "matching facts", fr: "faits correspondants", ar: "\u062D\u0642\u0627\u0626\u0642 \u0645\u0637\u0627\u0628\u0642\u0629", hi: "\u092E\u0947\u0932 \u0916\u093E\u0924\u0947 \u0924\u0925\u094D\u092F" },
  "comparativeAnalysis.rankedBySep": { en: "ranked by", fr: "class\xE9s par", ar: "\u0645\u0631\u062A\u0651\u0628\u0629 \u062D\u0633\u0628", hi: "\u0915\u094D\u0930\u092E\u092C\u0926\u094D\u0927" },
  "comparativeAnalysis.tierSep": { en: "tier", fr: "niveau", ar: "\u0627\u0644\u0645\u0633\u062A\u0648\u0649", hi: "\u0936\u094D\u0930\u0947\u0923\u0940" },
  "comparativeAnalysis.countUp": { en: "{0} up", fr: "{0} en hausse", ar: "{0} \u0627\u0631\u062A\u0641\u0639\u062A", hi: "{0} \u092C\u0922\u093C\u0947" },
  "comparativeAnalysis.countDown": { en: "{0} down", fr: "{0} en baisse", ar: "{0} \u0627\u0646\u062E\u0641\u0636\u062A", hi: "{0} \u0918\u091F\u0947" },
  "comparativeAnalysis.countUnchanged": { en: "{0} unchanged", fr: "{0} inchang\xE9s", ar: "{0} \u062F\u0648\u0646 \u062A\u063A\u064A\u064A\u0631", hi: "{0} \u0905\u092A\u0930\u093F\u0935\u0930\u094D\u0924\u093F\u0924" },
  "comparativeAnalysis.directionCountsNote": { en: "(direction counts cover all {0} facts)", fr: "(les compteurs de direction couvrent les {0} faits)", ar: "(\u062A\u0634\u0645\u0644 \u0639\u062F\u0627\u062F\u0627\u062A \u0627\u0644\u0627\u062A\u062C\u0627\u0647 \u062C\u0645\u064A\u0639 \u0627\u0644\u062D\u0642\u0627\u0626\u0642 \u0627\u0644\u0628\u0627\u0644\u063A\u0629 {0})", hi: "(\u0926\u093F\u0936\u093E \u0917\u0923\u0928\u093E\u090F\u0901 \u0938\u092D\u0940 {0} \u0924\u0925\u094D\u092F\u094B\u0902 \u0915\u094B \u0915\u0935\u0930 \u0915\u0930\u0924\u0940 \u0939\u0948\u0902)" },
  "comparativeAnalysis.topN": { en: "Top {0}", fr: "{0} principaux", ar: "\u0623\u0639\u0644\u0649 {0}", hi: "\u0936\u0940\u0930\u094D\u0937 {0}" },
  "comparativeAnalysis.previousWas0Count": { en: "Previous was 0 ({0})", fr: "Pr\xE9c\xE9dent \xE9tait 0 ({0})", ar: "\u0627\u0644\u0633\u0627\u0628\u0642 \u0643\u0627\u0646 0 ({0})", hi: "\u092A\u093F\u091B\u0932\u093E 0 \u0925\u093E ({0})" },
  "comparativeAnalysis.everyFactDrawn": { en: "Every comparable fact is drawn below.", fr: "Tous les faits comparables sont trac\xE9s ci-dessous.", ar: "\u0643\u0644 \u062D\u0642\u064A\u0642\u0629 \u0642\u0627\u0628\u0644\u0629 \u0644\u0644\u0645\u0642\u0627\u0631\u0646\u0629 \u0645\u0631\u0633\u0648\u0645\u0629 \u0623\u062F\u0646\u0627\u0647.", hi: "\u0939\u0930 \u0924\u0941\u0932\u0928\u0940\u092F \u0924\u0925\u094D\u092F \u0928\u0940\u091A\u0947 \u0926\u093F\u0916\u093E\u092F\u093E \u0917\u092F\u093E \u0939\u0948\u0964" },
  "comparativeAnalysis.zeroBaselineNote": { en: "Reported in both periods, but the previous value was 0 \u2014 so there is no percentage change to compute. These are real comparisons, not missing facts.", fr: "D\xE9clar\xE9s sur les deux p\xE9riodes, mais la valeur pr\xE9c\xE9dente \xE9tait 0 \u2014 il n\u2019y a donc aucune variation en pourcentage \xE0 calculer. Ce sont de vraies comparaisons, pas des faits manquants.", ar: "\u0645\u064F\u0628\u0644\u063A \u0639\u0646\u0647\u0627 \u0641\u064A \u0643\u0644\u062A\u0627 \u0627\u0644\u0641\u062A\u0631\u062A\u064A\u0646\u060C \u0644\u0643\u0646 \u0627\u0644\u0642\u064A\u0645\u0629 \u0627\u0644\u0633\u0627\u0628\u0642\u0629 \u0643\u0627\u0646\u062A 0 \u2014 \u0644\u0630\u0627 \u0644\u0627 \u062A\u0648\u062C\u062F \u0646\u0633\u0628\u0629 \u062A\u063A\u064A\u0651\u0631 \u0644\u062D\u0633\u0627\u0628\u0647\u0627. \u0647\u0630\u0647 \u0645\u0642\u0627\u0631\u0646\u0627\u062A \u062D\u0642\u064A\u0642\u064A\u0629 \u0648\u0644\u064A\u0633\u062A \u062D\u0642\u0627\u0626\u0642 \u0645\u0641\u0642\u0648\u062F\u0629.", hi: "\u0926\u094B\u0928\u094B\u0902 \u0905\u0935\u0927\u093F\u092F\u094B\u0902 \u092E\u0947\u0902 \u0926\u0930\u094D\u091C, \u0932\u0947\u0915\u093F\u0928 \u092A\u093F\u091B\u0932\u093E \u092E\u093E\u0928 0 \u0925\u093E \u2014 \u0907\u0938\u0932\u093F\u090F \u0917\u0923\u0928\u093E \u0915\u0930\u0928\u0947 \u0915\u0947 \u0932\u093F\u090F \u0915\u094B\u0908 \u092A\u094D\u0930\u0924\u093F\u0936\u0924 \u092A\u0930\u093F\u0935\u0930\u094D\u0924\u0928 \u0928\u0939\u0940\u0902 \u0939\u0948\u0964 \u092F\u0947 \u0935\u093E\u0938\u094D\u0924\u0935\u093F\u0915 \u0924\u0941\u0932\u0928\u093E\u090F\u0901 \u0939\u0948\u0902, \u0905\u0928\u0941\u092A\u0932\u092C\u094D\u0927 \u0924\u0925\u094D\u092F \u0928\u0939\u0940\u0902\u0964" },
  // ── chart tooltip ────────────────────────────────────────────────────────
  "comparativeAnalysis.tooltipCurrent": { en: "current", fr: "actuel", ar: "\u0627\u0644\u062D\u0627\u0644\u064A", hi: "\u0935\u0930\u094D\u0924\u092E\u093E\u0928" },
  "comparativeAnalysis.tooltipPrevious": { en: "previous", fr: "pr\xE9c\xE9dent", ar: "\u0627\u0644\u0633\u0627\u0628\u0642", hi: "\u092A\u093F\u091B\u0932\u093E" },
  "comparativeAnalysis.exactChange": { en: "Exact change", fr: "Variation exacte", ar: "\u0627\u0644\u062A\u063A\u064A\u0651\u0631 \u0627\u0644\u062F\u0642\u064A\u0642", hi: "\u0938\u091F\u0940\u0915 \u092A\u0930\u093F\u0935\u0930\u094D\u0924\u0928" },
  "comparativeAnalysis.tooltipChange": { en: "Change", fr: "Variation", ar: "\u0627\u0644\u062A\u063A\u064A\u0651\u0631", hi: "\u092A\u0930\u093F\u0935\u0930\u094D\u0924\u0928" },
  "comparativeAnalysis.tooltipDifference": { en: "Difference", fr: "\xC9cart", ar: "\u0627\u0644\u0641\u0631\u0642", hi: "\u0905\u0902\u0924\u0930" },
  "comparativeAnalysis.tooltipDirection": { en: "Direction", fr: "Sens", ar: "\u0627\u0644\u0627\u062A\u062C\u0627\u0647", hi: "\u0926\u093F\u0936\u093E" },
  "comparativeAnalysis.tooltipSignReversal": { en: "Sign reversal", fr: "Inversion de signe", ar: "\u0627\u0646\u0639\u0643\u0627\u0633 \u0627\u0644\u0625\u0634\u0627\u0631\u0629", hi: "\u091A\u093F\u0939\u094D\u0928 \u0909\u0932\u091F\u093E\u0935" },
  "comparativeAnalysis.sortHint": { en: "Click again to restore the default order.", fr: "Cliquez \xE0 nouveau pour r\xE9tablir l\u2019ordre par d\xE9faut.", ar: "\u0627\u0646\u0642\u0631 \u0645\u0631\u0629 \u0623\u062E\u0631\u0649 \u0644\u0627\u0633\u062A\u0639\u0627\u062F\u0629 \u0627\u0644\u062A\u0631\u062A\u064A\u0628 \u0627\u0644\u0627\u0641\u062A\u0631\u0627\u0636\u064A.", hi: "\u0921\u093F\u092B\u093C\u0949\u0932\u094D\u091F \u0915\u094D\u0930\u092E \u092C\u0939\u093E\u0932 \u0915\u0930\u0928\u0947 \u0915\u0947 \u0932\u093F\u090F \u092B\u093F\u0930 \u0938\u0947 \u0915\u094D\u0932\u093F\u0915 \u0915\u0930\u0947\u0902\u0964" },
  // ── exported HTML report ─────────────────────────────────────────────────
  "export.visualizationAll": { en: "Visualization: all {0} comparable facts", fr: "Visualisation : les {0} faits comparables", ar: "\u0627\u0644\u0639\u0631\u0636 \u0627\u0644\u0645\u0631\u0626\u064A: \u062C\u0645\u064A\u0639 \u0627\u0644\u062D\u0642\u0627\u0626\u0642 \u0627\u0644\u0642\u0627\u0628\u0644\u0629 \u0644\u0644\u0645\u0642\u0627\u0631\u0646\u0629 \u0627\u0644\u0628\u0627\u0644\u063A\u0629 {0}", hi: "\u0935\u093F\u091C\u093C\u0941\u0905\u0932\u093E\u0907\u091C\u093C\u0947\u0936\u0928: \u0938\u092D\u0940 {0} \u0924\u0941\u0932\u0928\u0940\u092F \u0924\u0925\u094D\u092F" },
  "export.oneSidedExcluded": { en: "{0} fact(s) reported in only one period are excluded \u2014 they cannot be compared.", fr: "{0} fait(s) d\xE9clar\xE9(s) sur une seule p\xE9riode sont exclus \u2014 ils ne peuvent pas \xEAtre compar\xE9s.", ar: "\u062A\u0645 \u0627\u0633\u062A\u0628\u0639\u0627\u062F {0} \u0645\u0646 \u0627\u0644\u062D\u0642\u0627\u0626\u0642 \u0627\u0644\u0645\u064F\u0628\u0644\u063A \u0639\u0646\u0647\u0627 \u0641\u064A \u0641\u062A\u0631\u0629 \u0648\u0627\u062D\u062F\u0629 \u0641\u0642\u0637 \u2014 \u0644\u0627 \u064A\u0645\u0643\u0646 \u0645\u0642\u0627\u0631\u0646\u062A\u0647\u0627.", hi: "\u0915\u0947\u0935\u0932 \u090F\u0915 \u0905\u0935\u0927\u093F \u092E\u0947\u0902 \u0926\u0930\u094D\u091C {0} \u0924\u0925\u094D\u092F \u092C\u093E\u0939\u0930 \u0930\u0916\u0947 \u0917\u090F \u0939\u0948\u0902 \u2014 \u0909\u0928\u0915\u0940 \u0924\u0941\u0932\u0928\u093E \u0928\u0939\u0940\u0902 \u0915\u0940 \u091C\u093E \u0938\u0915\u0924\u0940\u0964" },
  "export.generatedFrom": { en: "Generated from the {0} Critical and High regulatory-importance concept(s) in this comparison.", fr: "G\xE9n\xE9r\xE9 \xE0 partir des {0} concept(s) d\u2019importance r\xE9glementaire Critique et \xC9lev\xE9e de cette comparaison.", ar: "\u062A\u0645 \u0625\u0646\u0634\u0627\u0624\u0647 \u0645\u0646 {0} \u0645\u0646 \u0627\u0644\u0645\u0641\u0627\u0647\u064A\u0645 \u0630\u0627\u062A \u0627\u0644\u0623\u0647\u0645\u064A\u0629 \u0627\u0644\u062A\u0646\u0638\u064A\u0645\u064A\u0629 \u0627\u0644\u062D\u0631\u062C\u0629 \u0648\u0627\u0644\u0645\u0631\u062A\u0641\u0639\u0629 \u0641\u064A \u0647\u0630\u0647 \u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0629.", hi: "\u0907\u0938 \u0924\u0941\u0932\u0928\u093E \u0915\u0947 {0} \u0915\u094D\u0930\u093F\u091F\u093F\u0915\u0932 \u0914\u0930 \u0909\u091A\u094D\u091A \u0928\u093F\u092F\u093E\u092E\u0915-\u092E\u0939\u0924\u094D\u0935 \u0905\u0935\u0927\u093E\u0930\u0923\u093E\u0913\u0902 \u0938\u0947 \u092C\u0928\u093E\u092F\u093E \u0917\u092F\u093E\u0964" },
  "export.graphLimitedCritical": { en: "Graph limited to Critical regulatory-importance concepts.", fr: "Graphique limit\xE9 aux concepts d\u2019importance r\xE9glementaire Critique.", ar: "\u0627\u0644\u0631\u0633\u0645 \u0627\u0644\u0628\u064A\u0627\u0646\u064A \u0645\u0642\u062A\u0635\u0631 \u0639\u0644\u0649 \u0627\u0644\u0645\u0641\u0627\u0647\u064A\u0645 \u0630\u0627\u062A \u0627\u0644\u0623\u0647\u0645\u064A\u0629 \u0627\u0644\u062A\u0646\u0638\u064A\u0645\u064A\u0629 \u0627\u0644\u062D\u0631\u062C\u0629.", hi: "\u0917\u094D\u0930\u093E\u092B\u093C \u0915\u0947\u0935\u0932 \u0915\u094D\u0930\u093F\u091F\u093F\u0915\u0932 \u0928\u093F\u092F\u093E\u092E\u0915-\u092E\u0939\u0924\u094D\u0935 \u0905\u0935\u0927\u093E\u0930\u0923\u093E\u0913\u0902 \u0924\u0915 \u0938\u0940\u092E\u093F\u0924\u0964" },
  "export.criticalConcepts": { en: "Critical concepts", fr: "Concepts critiques", ar: "\u0627\u0644\u0645\u0641\u0627\u0647\u064A\u0645 \u0627\u0644\u062D\u0631\u062C\u0629", hi: "\u0915\u094D\u0930\u093F\u091F\u093F\u0915\u0932 \u0905\u0935\u0927\u093E\u0930\u0923\u093E\u090F\u0901" },
  "export.currentVsPrevious": { en: "Current vs previous", fr: "Actuel vs pr\xE9c\xE9dent", ar: "\u0627\u0644\u062D\u0627\u0644\u064A \u0645\u0642\u0627\u0628\u0644 \u0627\u0644\u0633\u0627\u0628\u0642", hi: "\u0935\u0930\u094D\u0924\u092E\u093E\u0928 \u092C\u0928\u093E\u092E \u092A\u093F\u091B\u0932\u093E" },
  // ── errors / voice / misc UI ─────────────────────────────────────────────
  "errors.downloadReport": { en: "Download error report", fr: "T\xE9l\xE9charger le rapport d\u2019erreurs", ar: "\u062A\u0646\u0632\u064A\u0644 \u062A\u0642\u0631\u064A\u0631 \u0627\u0644\u0623\u062E\u0637\u0627\u0621", hi: "\u0924\u094D\u0930\u0941\u091F\u093F \u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0921\u093E\u0909\u0928\u0932\u094B\u0921 \u0915\u0930\u0947\u0902" },
  "errors.explainFormula": { en: "Explain Formula Errors", fr: "Expliquer les erreurs de formule", ar: "\u0634\u0631\u062D \u0623\u062E\u0637\u0627\u0621 \u0627\u0644\u0635\u064A\u063A\u0629", hi: "\u0938\u0942\u0924\u094D\u0930 \u0924\u094D\u0930\u0941\u091F\u093F\u092F\u093E\u0901 \u0938\u092E\u091D\u093E\u090F\u0901" },
  "schedule.pickDate": { en: "Schedule date", fr: "Date de planification", ar: "\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u062C\u062F\u0648\u0644\u0629", hi: "\u0936\u0947\u0921\u094D\u092F\u0942\u0932 \u0915\u0940 \u0924\u093E\u0930\u0940\u0916" },
  "schedule.done": { en: "Done", fr: "Termin\xE9", ar: "\u062A\u0645", hi: "\u0939\u094B \u0917\u092F\u093E" },
  "schedule.pickTime": { en: "Schedule time", fr: "Heure de planification", ar: "\u0648\u0642\u062A \u0627\u0644\u062C\u062F\u0648\u0644\u0629", hi: "\u0936\u0947\u0921\u094D\u092F\u0942\u0932 \u0915\u093E \u0938\u092E\u092F" },
  "schedule.timeHint": { en: "HH : MM : SS  (hour : minute : second)", fr: "HH : MM : SS  (heure : minute : seconde)", ar: "HH : MM : SS  (\u0633\u0627\u0639\u0629 : \u062F\u0642\u064A\u0642\u0629 : \u062B\u0627\u0646\u064A\u0629)", hi: "HH : MM : SS  (\u0918\u0902\u091F\u093E : \u092E\u093F\u0928\u091F : \u0938\u0947\u0915\u0902\u0921)" },
  "schedule.setSchedule": { en: "Use this date and time", fr: "Utiliser cette date et cette heure", ar: "\u0627\u0633\u062A\u062E\u062F\u0645 \u0647\u0630\u0627 \u0627\u0644\u062A\u0627\u0631\u064A\u062E \u0648\u0627\u0644\u0648\u0642\u062A", hi: "\u092F\u0939 \u0924\u093E\u0930\u0940\u0916 \u0914\u0930 \u0938\u092E\u092F \u0909\u092A\u092F\u094B\u0917 \u0915\u0930\u0947\u0902" },
  "schedule.mustBeFuture": { en: "The schedule date and time must be in the future.", fr: "La date et l\u2019heure de planification doivent \xEAtre dans le futur.", ar: "\u064A\u062C\u0628 \u0623\u0646 \u064A\u0643\u0648\u0646 \u062A\u0627\u0631\u064A\u062E \u0627\u0644\u062C\u062F\u0648\u0644\u0629 \u0648\u0648\u0642\u062A\u0647\u0627 \u0641\u064A \u0627\u0644\u0645\u0633\u062A\u0642\u0628\u0644.", hi: "\u0936\u0947\u0921\u094D\u092F\u0942\u0932 \u0915\u0940 \u0924\u093E\u0930\u0940\u0916 \u0914\u0930 \u0938\u092E\u092F \u092D\u0935\u093F\u0937\u094D\u092F \u092E\u0947\u0902 \u0939\u094B\u0928\u093E \u091A\u093E\u0939\u093F\u090F\u0964" },
  "errors.explainSchema": { en: "Explain Schema Errors", fr: "Expliquer les erreurs de sch\xE9ma", ar: "\u0634\u0631\u062D \u0623\u062E\u0637\u0627\u0621 \u0627\u0644\u0645\u062E\u0637\u0637", hi: "\u0938\u094D\u0915\u0940\u092E\u093E \u0924\u094D\u0930\u0941\u091F\u093F\u092F\u093E\u0901 \u0938\u092E\u091D\u093E\u090F\u0901" },
  "errors.explainDimension": { en: "Explain Dimension Errors", fr: "Expliquer les erreurs de dimension", ar: "\u0634\u0631\u062D \u0623\u062E\u0637\u0627\u0621 \u0627\u0644\u0623\u0628\u0639\u0627\u062F", hi: "\u0906\u092F\u093E\u092E \u0924\u094D\u0930\u0941\u091F\u093F\u092F\u093E\u0901 \u0938\u092E\u091D\u093E\u090F\u0901" },
  "errors.failureReasons": { en: "Failure Reason(s):", fr: "Motif(s) de l\u2019\xE9chec :", ar: "\u0623\u0633\u0628\u0627\u0628 \u0627\u0644\u0641\u0634\u0644:", hi: "\u0935\u093F\u092B\u0932\u0924\u093E \u0915\u0947 \u0915\u093E\u0930\u0923:" },
  "errors.whatIsWrong": { en: "What is wrong", fr: "Ce qui ne va pas", ar: "\u0645\u0627 \u0627\u0644\u062E\u0637\u0623", hi: "\u0915\u094D\u092F\u093E \u0917\u0932\u0924 \u0939\u0948" },
  "errors.whatShouldBeChecked": { en: "What should be checked", fr: "Ce qu\u2019il faut v\xE9rifier", ar: "\u0645\u0627 \u0627\u0644\u0630\u064A \u064A\u0646\u0628\u063A\u064A \u0627\u0644\u062A\u062D\u0642\u0642 \u0645\u0646\u0647", hi: "\u0915\u094D\u092F\u093E \u091C\u093E\u0901\u091A\u0928\u093E \u091A\u093E\u0939\u093F\u090F" },
  "errors.reportedValue": { en: "Reported value", fr: "Valeur d\xE9clar\xE9e", ar: "\u0627\u0644\u0642\u064A\u0645\u0629 \u0627\u0644\u0645\u064F\u0628\u0644\u063A \u0639\u0646\u0647\u0627", hi: "\u0926\u0930\u094D\u091C \u0915\u093F\u092F\u093E \u0917\u092F\u093E \u092E\u093E\u0928" },
  "errors.sqlValidationFailed": { en: "SQL validation failed.", fr: "La validation SQL a \xE9chou\xE9.", ar: "\u0641\u0634\u0644 \u0627\u0644\u062A\u062D\u0642\u0642 \u0645\u0646 SQL.", hi: "SQL \u0938\u0924\u094D\u092F\u093E\u092A\u0928 \u0935\u093F\u092B\u0932 \u0930\u0939\u093E\u0964" },
  "variance.aiUnavailable": { en: "AI analysis is unavailable for this comparison. The variance table and chart above are complete.", fr: "L\u2019analyse IA n\u2019est pas disponible pour cette comparaison. Le tableau et le graphique des \xE9carts ci-dessus sont complets.", ar: "\u062A\u062D\u0644\u064A\u0644 \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064A \u063A\u064A\u0631 \u0645\u062A\u0627\u062D \u0644\u0647\u0630\u0647 \u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0629. \u062C\u062F\u0648\u0644 \u0627\u0644\u0641\u0631\u0648\u0642\u0627\u062A \u0648\u0627\u0644\u0645\u062E\u0637\u0637 \u0623\u0639\u0644\u0627\u0647 \u0645\u0643\u062A\u0645\u0644\u0627\u0646.", hi: "\u0907\u0938 \u0924\u0941\u0932\u0928\u093E \u0915\u0947 \u0932\u093F\u090F AI \u0935\u093F\u0936\u094D\u0932\u0947\u0937\u0923 \u0909\u092A\u0932\u092C\u094D\u0927 \u0928\u0939\u0940\u0902 \u0939\u0948\u0964 \u090A\u092A\u0930 \u0926\u0940 \u0917\u0908 \u092D\u093F\u0928\u094D\u0928\u0924\u093E \u0924\u093E\u0932\u093F\u0915\u093E \u0914\u0930 \u091A\u093E\u0930\u094D\u091F \u092A\u0942\u0930\u094D\u0923 \u0939\u0948\u0902\u0964" },
  "variance.chooseTwoInstances": { en: "Choose two different instances to compare.", fr: "Choisissez deux instances diff\xE9rentes \xE0 comparer.", ar: "\u0627\u062E\u062A\u0631 \u0646\u0633\u062E\u062A\u064A\u0646 \u0645\u062E\u062A\u0644\u0641\u062A\u064A\u0646 \u0644\u0644\u0645\u0642\u0627\u0631\u0646\u0629.", hi: "\u0924\u0941\u0932\u0928\u093E \u0915\u0947 \u0932\u093F\u090F \u0926\u094B \u0905\u0932\u0917-\u0905\u0932\u0917 \u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 \u091A\u0941\u0928\u0947\u0902\u0964" },
  "variance.selectEachDropdown": { en: "Select an instance in each dropdown.", fr: "S\xE9lectionnez une instance dans chaque liste d\xE9roulante.", ar: "\u0627\u062E\u062A\u0631 \u0646\u0633\u062E\u0629 \u0645\u0646 \u0643\u0644 \u0642\u0627\u0626\u0645\u0629 \u0645\u0646\u0633\u062F\u0644\u0629.", hi: "\u092A\u094D\u0930\u0924\u094D\u092F\u0947\u0915 \u0921\u094D\u0930\u0949\u092A\u0921\u093E\u0909\u0928 \u092E\u0947\u0902 \u090F\u0915 \u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 \u091A\u0941\u0928\u0947\u0902\u0964" },
  "variance.selectInstancePlaceholder": { en: "\u2014 Select instance \u2014", fr: "\u2014 S\xE9lectionner une instance \u2014", ar: "\u2014 \u0627\u062E\u062A\u0631 \u0646\u0633\u062E\u0629 \u2014", hi: "\u2014 \u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 \u091A\u0941\u0928\u0947\u0902 \u2014" },
  "variance.noPctZeroBaseline": { en: "No % change (zero baseline)", fr: "Aucune variation en % (base nulle)", ar: "\u0644\u0627 \u062A\u063A\u064A\u0651\u0631 \u0628\u0627\u0644\u0646\u0633\u0628\u0629 \u0627\u0644\u0645\u0626\u0648\u064A\u0629 (\u0623\u0633\u0627\u0633 \u0635\u0641\u0631\u064A)", hi: "\u0915\u094B\u0908 % \u092A\u0930\u093F\u0935\u0930\u094D\u0924\u0928 \u0928\u0939\u0940\u0902 (\u0936\u0942\u0928\u094D\u092F \u0906\u0927\u093E\u0930)" },
  "variance.toSeeEveryTier": { en: "to see every tier.", fr: "pour voir tous les niveaux.", ar: "\u0644\u0639\u0631\u0636 \u062C\u0645\u064A\u0639 \u0627\u0644\u0645\u0633\u062A\u0648\u064A\u0627\u062A.", hi: "\u0938\u092D\u0940 \u0936\u094D\u0930\u0947\u0923\u093F\u092F\u093E\u0901 \u0926\u0947\u0916\u0928\u0947 \u0915\u0947 \u0932\u093F\u090F\u0964" },
  "voice.micRequired": { en: "Microphone access is required to use voice input.", fr: "L\u2019acc\xE8s au microphone est requis pour la saisie vocale.", ar: "\u0627\u0644\u0648\u0635\u0648\u0644 \u0625\u0644\u0649 \u0627\u0644\u0645\u064A\u0643\u0631\u0648\u0641\u0648\u0646 \u0645\u0637\u0644\u0648\u0628 \u0644\u0627\u0633\u062A\u062E\u062F\u0627\u0645 \u0627\u0644\u0625\u062F\u062E\u0627\u0644 \u0627\u0644\u0635\u0648\u062A\u064A.", hi: "\u0935\u0949\u0907\u0938 \u0907\u0928\u092A\u0941\u091F \u0915\u0947 \u0932\u093F\u090F \u092E\u093E\u0907\u0915\u094D\u0930\u094B\u092B\u093C\u094B\u0928 \u090F\u0915\u094D\u0938\u0947\u0938 \u0906\u0935\u0936\u094D\u092F\u0915 \u0939\u0948\u0964" },
  "voice.transcribeFailed": { en: "Voice transcription failed. Please try again.", fr: "La transcription vocale a \xE9chou\xE9. Veuillez r\xE9essayer.", ar: "\u0641\u0634\u0644 \u0627\u0644\u062A\u0641\u0631\u064A\u063A \u0627\u0644\u0635\u0648\u062A\u064A. \u064A\u0631\u062C\u0649 \u0627\u0644\u0645\u062D\u0627\u0648\u0644\u0629 \u0645\u0631\u0629 \u0623\u062E\u0631\u0649.", hi: "\u0935\u0949\u0907\u0938 \u091F\u094D\u0930\u093E\u0902\u0938\u0915\u094D\u0930\u093F\u092A\u094D\u0936\u0928 \u0935\u093F\u092B\u0932 \u0930\u0939\u093E\u0964 \u0915\u0943\u092A\u092F\u093E \u092A\u0941\u0928\u0903 \u092A\u094D\u0930\u092F\u093E\u0938 \u0915\u0930\u0947\u0902\u0964" },
  "voice.notHeard": { en: "We could not hear your speech clearly. Please try again.", fr: "Nous n\u2019avons pas bien entendu votre voix. Veuillez r\xE9essayer.", ar: "\u0644\u0645 \u0646\u062A\u0645\u0643\u0646 \u0645\u0646 \u0633\u0645\u0627\u0639 \u0643\u0644\u0627\u0645\u0643 \u0628\u0648\u0636\u0648\u062D. \u064A\u0631\u062C\u0649 \u0627\u0644\u0645\u062D\u0627\u0648\u0644\u0629 \u0645\u0631\u0629 \u0623\u062E\u0631\u0649.", hi: "\u0939\u092E \u0906\u092A\u0915\u0940 \u0906\u0935\u093E\u091C\u093C \u0938\u094D\u092A\u0937\u094D\u091F \u0930\u0942\u092A \u0938\u0947 \u0928\u0939\u0940\u0902 \u0938\u0941\u0928 \u0938\u0915\u0947\u0964 \u0915\u0943\u092A\u092F\u093E \u092A\u0941\u0928\u0903 \u092A\u094D\u0930\u092F\u093E\u0938 \u0915\u0930\u0947\u0902\u0964" },
  "errors.fetchActions": { en: "Failed to fetch allowed actions", fr: "\xC9chec de la r\xE9cup\xE9ration des actions autoris\xE9es", ar: "\u062A\u0639\u0630\u0651\u0631 \u062C\u0644\u0628 \u0627\u0644\u0625\u062C\u0631\u0627\u0621\u0627\u062A \u0627\u0644\u0645\u0633\u0645\u0648\u062D \u0628\u0647\u0627", hi: "\u0905\u0928\u0941\u092E\u0924 \u0915\u094D\u0930\u093F\u092F\u093E\u090F\u0901 \u092A\u094D\u0930\u093E\u092A\u094D\u0924 \u0915\u0930\u0928\u0947 \u092E\u0947\u0902 \u0935\u093F\u092B\u0932" },
  "errors.compareFailed": { en: "We could not compare those instances right now. Please try again.", fr: "Nous n\u2019avons pas pu comparer ces instances pour le moment. Veuillez r\xE9essayer.", ar: "\u062A\u0639\u0630\u0651\u0631\u062A \u0645\u0642\u0627\u0631\u0646\u0629 \u0647\u0627\u062A\u064A\u0646 \u0627\u0644\u0646\u0633\u062E\u062A\u064A\u0646 \u062D\u0627\u0644\u064A\u064B\u0627. \u064A\u0631\u062C\u0649 \u0627\u0644\u0645\u062D\u0627\u0648\u0644\u0629 \u0645\u0631\u0629 \u0623\u062E\u0631\u0649.", hi: "\u0905\u092D\u0940 \u0909\u0928 \u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 \u0915\u0940 \u0924\u0941\u0932\u0928\u093E \u0928\u0939\u0940\u0902 \u0915\u0940 \u091C\u093E \u0938\u0915\u0940\u0964 \u0915\u0943\u092A\u092F\u093E \u092A\u0941\u0928\u0903 \u092A\u094D\u0930\u092F\u093E\u0938 \u0915\u0930\u0947\u0902\u0964" },
  "errors.explanationFailed": { en: "We could not load the explanation right now. Please try again.", fr: "Nous n\u2019avons pas pu charger l\u2019explication pour le moment. Veuillez r\xE9essayer.", ar: "\u062A\u0639\u0630\u0651\u0631 \u062A\u062D\u0645\u064A\u0644 \u0627\u0644\u0634\u0631\u062D \u062D\u0627\u0644\u064A\u064B\u0627. \u064A\u0631\u062C\u0649 \u0627\u0644\u0645\u062D\u0627\u0648\u0644\u0629 \u0645\u0631\u0629 \u0623\u062E\u0631\u0649.", hi: "\u0905\u092D\u0940 \u0938\u094D\u092A\u0937\u094D\u091F\u0940\u0915\u0930\u0923 \u0932\u094B\u0921 \u0928\u0939\u0940\u0902 \u0915\u093F\u092F\u093E \u091C\u093E \u0938\u0915\u093E\u0964 \u0915\u0943\u092A\u092F\u093E \u092A\u0941\u0928\u0903 \u092A\u094D\u0930\u092F\u093E\u0938 \u0915\u0930\u0947\u0902\u0964" },
  "errors.requestFailed": { en: "We could not process your request right now. Please try again.", fr: "Nous n\u2019avons pas pu traiter votre demande pour le moment. Veuillez r\xE9essayer.", ar: "\u062A\u0639\u0630\u0651\u0631\u062A \u0645\u0639\u0627\u0644\u062C\u0629 \u0637\u0644\u0628\u0643 \u062D\u0627\u0644\u064A\u064B\u0627. \u064A\u0631\u062C\u0649 \u0627\u0644\u0645\u062D\u0627\u0648\u0644\u0629 \u0645\u0631\u0629 \u0623\u062E\u0631\u0649.", hi: "\u0905\u092D\u0940 \u0906\u092A\u0915\u093E \u0905\u0928\u0941\u0930\u094B\u0927 \u0938\u0902\u0938\u093E\u0927\u093F\u0924 \u0928\u0939\u0940\u0902 \u0915\u093F\u092F\u093E \u091C\u093E \u0938\u0915\u093E\u0964 \u0915\u0943\u092A\u092F\u093E \u092A\u0941\u0928\u0903 \u092A\u094D\u0930\u092F\u093E\u0938 \u0915\u0930\u0947\u0902\u0964" },
  "common.disclaimer": { en: "AI-generated responses may be inaccurate \u2014 please verify important details against the application.", fr: "Les r\xE9ponses g\xE9n\xE9r\xE9es par l\u2019IA peuvent \xEAtre inexactes \u2014 veuillez v\xE9rifier les informations importantes dans l\u2019application.", ar: "\u0642\u062F \u062A\u0643\u0648\u0646 \u0627\u0644\u0631\u062F\u0648\u062F \u0627\u0644\u0645\u0648\u0644\u0651\u062F\u0629 \u0628\u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064A \u063A\u064A\u0631 \u062F\u0642\u064A\u0642\u0629 \u2014 \u064A\u0631\u062C\u0649 \u0627\u0644\u062A\u062D\u0642\u0642 \u0645\u0646 \u0627\u0644\u062A\u0641\u0627\u0635\u064A\u0644 \u0627\u0644\u0645\u0647\u0645\u0629 \u0641\u064A \u0627\u0644\u062A\u0637\u0628\u064A\u0642.", hi: "AI-\u091C\u0928\u093F\u0924 \u0909\u0924\u094D\u0924\u0930 \u0917\u0932\u0924 \u0939\u094B \u0938\u0915\u0924\u0947 \u0939\u0948\u0902 \u2014 \u0915\u0943\u092A\u092F\u093E \u092E\u0939\u0924\u094D\u0935\u092A\u0942\u0930\u094D\u0923 \u0935\u093F\u0935\u0930\u0923 \u090F\u092A\u094D\u0932\u093F\u0915\u0947\u0936\u0928 \u092E\u0947\u0902 \u0938\u0924\u094D\u092F\u093E\u092A\u093F\u0924 \u0915\u0930\u0947\u0902\u0964" },
  "comparativeAnalysis.factsBoth": { en: "{0} facts reported in BOTH {1} and {2}.", fr: "{0} faits d\xE9clar\xE9s dans {1} ET {2}.", ar: "{0} \u062D\u0642\u064A\u0642\u0629 \u0645\u064F\u0628\u0644\u063A \u0639\u0646\u0647\u0627 \u0641\u064A \u0643\u0644 \u0645\u0646 {1} \u0648{2}.", hi: "{1} \u0914\u0930 {2} \u0926\u094B\u0928\u094B\u0902 \u092E\u0947\u0902 \u0926\u0930\u094D\u091C {0} \u0924\u0925\u094D\u092F\u0964" },
  "comparativeAnalysis.oneSidedExcluded": { en: "{0} present in only one period \u2014 excluded, they cannot be compared.", fr: "{0} pr\xE9sents sur une seule p\xE9riode \u2014 exclus, ils ne peuvent pas \xEAtre compar\xE9s.", ar: "{0} \u0645\u0648\u062C\u0648\u062F\u0629 \u0641\u064A \u0641\u062A\u0631\u0629 \u0648\u0627\u062D\u062F\u0629 \u0641\u0642\u0637 \u2014 \u0645\u0633\u062A\u0628\u0639\u062F\u0629\u060C \u0644\u0627 \u064A\u0645\u0643\u0646 \u0645\u0642\u0627\u0631\u0646\u062A\u0647\u0627.", hi: "{0} \u0915\u0947\u0935\u0932 \u090F\u0915 \u0905\u0935\u0927\u093F \u092E\u0947\u0902 \u092E\u094C\u091C\u0942\u0926 \u2014 \u092C\u093E\u0939\u0930 \u0930\u0916\u0947 \u0917\u090F, \u0909\u0928\u0915\u0940 \u0924\u0941\u0932\u0928\u093E \u0928\u0939\u0940\u0902 \u0915\u0940 \u091C\u093E \u0938\u0915\u0924\u0940\u0964" },
  "comparativeAnalysis.dimensionalContext": { en: "{0} carry a dimensional context.", fr: "{0} portent un contexte dimensionnel.", ar: "{0} \u062A\u062D\u0645\u0644 \u0633\u064A\u0627\u0642\u064B\u0627 \u0628\u064F\u0639\u062F\u064A\u064B\u0627.", hi: "{0} \u092E\u0947\u0902 \u0906\u092F\u093E\u092E\u0940 \u0938\u0902\u0926\u0930\u094D\u092D \u0939\u0948\u0964" },
  "comparativeAnalysis.criticalConceptsOf": { en: "Critical concepts \u2014 {0} of {1} facts", fr: "Concepts critiques \u2014 {0} sur {1} faits", ar: "\u0627\u0644\u0645\u0641\u0627\u0647\u064A\u0645 \u0627\u0644\u062D\u0631\u062C\u0629 \u2014 {0} \u0645\u0646 {1} \u062D\u0642\u064A\u0642\u0629", hi: "\u0915\u094D\u0930\u093F\u091F\u093F\u0915\u0932 \u0905\u0935\u0927\u093E\u0930\u0923\u093E\u090F\u0901 \u2014 {1} \u092E\u0947\u0902 \u0938\u0947 {0} \u0924\u0925\u094D\u092F" },
  "comparativeAnalysis.currentVsPreviousAll": { en: "Current vs previous \u2014 all {0} facts", fr: "Actuel vs pr\xE9c\xE9dent \u2014 les {0} faits", ar: "\u0627\u0644\u062D\u0627\u0644\u064A \u0645\u0642\u0627\u0628\u0644 \u0627\u0644\u0633\u0627\u0628\u0642 \u2014 \u062C\u0645\u064A\u0639 \u0627\u0644\u062D\u0642\u0627\u0626\u0642 \u0627\u0644\u0628\u0627\u0644\u063A\u0629 {0}", hi: "\u0935\u0930\u094D\u0924\u092E\u093E\u0928 \u092C\u0928\u093E\u092E \u092A\u093F\u091B\u0932\u093E \u2014 \u0938\u092D\u0940 {0} \u0924\u0925\u094D\u092F" },
  "comparativeAnalysis.sortConcept": { en: "concept", fr: "concept", ar: "\u0627\u0644\u0645\u0641\u0647\u0648\u0645", hi: "\u0905\u0935\u0927\u093E\u0930\u0923\u093E" },
  "comparativeAnalysis.sortCurrent": { en: "current value", fr: "valeur actuelle", ar: "\u0627\u0644\u0642\u064A\u0645\u0629 \u0627\u0644\u062D\u0627\u0644\u064A\u0629", hi: "\u0935\u0930\u094D\u0924\u092E\u093E\u0928 \u092E\u093E\u0928" },
  "comparativeAnalysis.sortPrevious": { en: "previous value", fr: "valeur pr\xE9c\xE9dente", ar: "\u0627\u0644\u0642\u064A\u0645\u0629 \u0627\u0644\u0633\u0627\u0628\u0642\u0629", hi: "\u092A\u093F\u091B\u0932\u093E \u092E\u093E\u0928" },
  "comparativeAnalysis.sortDifference": { en: "difference", fr: "\xE9cart", ar: "\u0627\u0644\u0641\u0631\u0642", hi: "\u0905\u0902\u0924\u0930" },
  "comparativeAnalysis.sortPctChange": { en: "% change", fr: "% de variation", ar: "% \u0627\u0644\u062A\u063A\u064A\u0651\u0631", hi: "% \u092A\u0930\u093F\u0935\u0930\u094D\u0924\u0928" },
  "comparativeAnalysis.sortSeverity": { en: "severity", fr: "gravit\xE9", ar: "\u0627\u0644\u062E\u0637\u0648\u0631\u0629", hi: "\u0917\u0902\u092D\u0940\u0930\u0924\u093E" },
  "comparativeAnalysis.rawDiff": { en: "Raw diff", fr: "\xC9cart brut", ar: "\u0627\u0644\u0641\u0631\u0642 \u0627\u0644\u062E\u0627\u0645", hi: "\u0915\u091A\u094D\u091A\u093E \u0905\u0902\u0924\u0930" },
  "comparativeAnalysis.directionReversedLabel": { en: "Direction reversed", fr: "Sens invers\xE9", ar: "\u0627\u0646\u0639\u0643\u0633 \u0627\u0644\u0627\u062A\u062C\u0627\u0647", hi: "\u0926\u093F\u0936\u093E \u0909\u0932\u091F\u0940" },
  "comparativeAnalysis.zeroBaseTooltip": { en: "Previous period ({0}) was 0, so there is no percentage change to compute. The fact was reported in both periods \u2014 this is a real comparison, not missing data.", fr: "La p\xE9riode pr\xE9c\xE9dente ({0}) \xE9tait \xE0 0, il n\u2019y a donc aucune variation en pourcentage \xE0 calculer. Le fait a \xE9t\xE9 d\xE9clar\xE9 sur les deux p\xE9riodes \u2014 c\u2019est une vraie comparaison, pas une donn\xE9e manquante.", ar: "\u0643\u0627\u0646\u062A \u0627\u0644\u0641\u062A\u0631\u0629 \u0627\u0644\u0633\u0627\u0628\u0642\u0629 ({0}) \u062A\u0633\u0627\u0648\u064A 0\u060C \u0644\u0630\u0627 \u0644\u0627 \u062A\u0648\u062C\u062F \u0646\u0633\u0628\u0629 \u062A\u063A\u064A\u0651\u0631 \u0644\u062D\u0633\u0627\u0628\u0647\u0627. \u062A\u0645 \u0627\u0644\u0625\u0628\u0644\u0627\u063A \u0639\u0646 \u0627\u0644\u062D\u0642\u064A\u0642\u0629 \u0641\u064A \u0643\u0644\u062A\u0627 \u0627\u0644\u0641\u062A\u0631\u062A\u064A\u0646 \u2014 \u0647\u0630\u0647 \u0645\u0642\u0627\u0631\u0646\u0629 \u062D\u0642\u064A\u0642\u064A\u0629 \u0648\u0644\u064A\u0633\u062A \u0628\u064A\u0627\u0646\u0627\u062A \u0645\u0641\u0642\u0648\u062F\u0629.", hi: "\u092A\u093F\u091B\u0932\u0940 \u0905\u0935\u0927\u093F ({0}) 0 \u0925\u0940, \u0907\u0938\u0932\u093F\u090F \u0917\u0923\u0928\u093E \u0915\u0930\u0928\u0947 \u0915\u0947 \u0932\u093F\u090F \u0915\u094B\u0908 \u092A\u094D\u0930\u0924\u093F\u0936\u0924 \u092A\u0930\u093F\u0935\u0930\u094D\u0924\u0928 \u0928\u0939\u0940\u0902 \u0939\u0948\u0964 \u092F\u0939 \u0924\u0925\u094D\u092F \u0926\u094B\u0928\u094B\u0902 \u0905\u0935\u0927\u093F\u092F\u094B\u0902 \u092E\u0947\u0902 \u0926\u0930\u094D\u091C \u0915\u093F\u092F\u093E \u0917\u092F\u093E \u2014 \u092F\u0939 \u0935\u093E\u0938\u094D\u0924\u0935\u093F\u0915 \u0924\u0941\u0932\u0928\u093E \u0939\u0948, \u0905\u0928\u0941\u092A\u0932\u092C\u094D\u0927 \u0921\u0947\u091F\u093E \u0928\u0939\u0940\u0902\u0964" },
  "comparativeAnalysis.allCount": { en: "All ({0})", fr: "Tout ({0})", ar: "\u0627\u0644\u0643\u0644 ({0})", hi: "\u0938\u092D\u0940 ({0})" },
  "errors.validationRuleFailed": { en: "Validation rule '{0}' failed.", fr: "La r\xE8gle de validation \xAB {0} \xBB a \xE9chou\xE9.", ar: "\u0641\u0634\u0644\u062A \u0642\u0627\u0639\u062F\u0629 \u0627\u0644\u062A\u062D\u0642\u0642 \xAB{0}\xBB.", hi: "\u0938\u0924\u094D\u092F\u093E\u092A\u0928 \u0928\u093F\u092F\u092E '{0}' \u0935\u093F\u092B\u0932 \u0930\u0939\u093E\u0964" },
  "errors.ruleFailed": { en: "Rule '{0}' failed.", fr: "La r\xE8gle \xAB {0} \xBB a \xE9chou\xE9.", ar: "\u0641\u0634\u0644\u062A \u0627\u0644\u0642\u0627\u0639\u062F\u0629 \xAB{0}\xBB.", hi: "\u0928\u093F\u092F\u092E '{0}' \u0935\u093F\u092B\u0932 \u0930\u0939\u093E\u0964" },
  "errors.dimensionalDetected": { en: "Dimensional error detected for concept '{0}'.", fr: "Erreur dimensionnelle d\xE9tect\xE9e pour le concept \xAB {0} \xBB.", ar: "\u062A\u0645 \u0627\u0643\u062A\u0634\u0627\u0641 \u062E\u0637\u0623 \u0628\u064F\u0639\u062F\u064A \u0644\u0644\u0645\u0641\u0647\u0648\u0645 \xAB{0}\xBB.", hi: "\u0905\u0935\u0927\u093E\u0930\u0923\u093E '{0}' \u0915\u0947 \u0932\u093F\u090F \u0906\u092F\u093E\u092E\u0940 \u0924\u094D\u0930\u0941\u091F\u093F \u092A\u093E\u0908 \u0917\u0908\u0964" },
  "errors.unknownConcept": { en: "unknown", fr: "inconnu", ar: "\u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641", hi: "\u0905\u091C\u094D\u091E\u093E\u0924" },
  "support.sorry": { en: "I'm sorry the experience wasn't helpful.", fr: "Je suis d\xE9sol\xE9 que cette exp\xE9rience n\u2019ait pas \xE9t\xE9 utile.", ar: "\u064A\u0624\u0633\u0641\u0646\u064A \u0623\u0646 \u0627\u0644\u062A\u062C\u0631\u0628\u0629 \u0644\u0645 \u062A\u0643\u0646 \u0645\u0641\u064A\u062F\u0629.", hi: "\u0916\u0947\u0926 \u0939\u0948 \u0915\u093F \u092F\u0939 \u0905\u0928\u0941\u092D\u0935 \u0938\u0939\u093E\u092F\u0915 \u0928\u0939\u0940\u0902 \u0930\u0939\u093E\u0964" },
  "support.contact": { en: "If you're facing an issue, have a query, or want to report a problem, please contact our support team:", fr: "Si vous rencontrez un probl\xE8me, avez une question ou souhaitez signaler un incident, veuillez contacter notre \xE9quipe d\u2019assistance :", ar: "\u0625\u0630\u0627 \u0643\u0646\u062A \u062A\u0648\u0627\u062C\u0647 \u0645\u0634\u0643\u0644\u0629 \u0623\u0648 \u0644\u062F\u064A\u0643 \u0627\u0633\u062A\u0641\u0633\u0627\u0631 \u0623\u0648 \u062A\u0631\u064A\u062F \u0627\u0644\u0625\u0628\u0644\u0627\u063A \u0639\u0646 \u062E\u0644\u0644\u060C \u064A\u0631\u062C\u0649 \u0627\u0644\u062A\u0648\u0627\u0635\u0644 \u0645\u0639 \u0641\u0631\u064A\u0642 \u0627\u0644\u062F\u0639\u0645:", hi: "\u092F\u0926\u093F \u0906\u092A\u0915\u094B \u0915\u094B\u0908 \u0938\u092E\u0938\u094D\u092F\u093E \u0939\u0948, \u092A\u094D\u0930\u0936\u094D\u0928 \u0939\u0948, \u092F\u093E \u0915\u094B\u0908 \u092A\u0930\u0947\u0936\u093E\u0928\u0940 \u092C\u0924\u093E\u0928\u0940 \u0939\u0948, \u0924\u094B \u0915\u0943\u092A\u092F\u093E \u0939\u092E\u093E\u0930\u0940 \u0938\u0939\u093E\u092F\u0924\u093E \u091F\u0940\u092E \u0938\u0947 \u0938\u0902\u092A\u0930\u094D\u0915 \u0915\u0930\u0947\u0902:" },
  "comparativeAnalysis.moreRowsNotShown": { en: "{0} more rows not shown", fr: "{0} lignes suppl\xE9mentaires non affich\xE9es", ar: "{0} \u0635\u0641\u0648\u0641 \u0625\u0636\u0627\u0641\u064A\u0629 \u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0636\u0629", hi: "{0} \u0914\u0930 \u092A\u0902\u0915\u094D\u0924\u093F\u092F\u093E\u0901 \u0928\u0939\u0940\u0902 \u0926\u093F\u0916\u093E\u0908 \u0917\u0908\u0902" },
  "comparativeAnalysis.showAll": { en: "Show all {0}", fr: "Afficher les {0}", ar: "\u0639\u0631\u0636 \u0627\u0644\u0643\u0644 ({0})", hi: "\u0938\u092D\u0940 {0} \u0926\u093F\u0916\u093E\u090F\u0901" },
  "errors.summaryHeading": { en: "Error Summary", fr: "R\xE9sum\xE9 des erreurs", ar: "\u0645\u0644\u062E\u0635 \u0627\u0644\u0623\u062E\u0637\u0627\u0621", hi: "\u0924\u094D\u0930\u0941\u091F\u093F \u0938\u093E\u0930\u093E\u0902\u0936" },
  "errors.explainNext": { en: "Explain Next Errors", fr: "Expliquer les erreurs suivantes", ar: "\u0634\u0631\u062D \u0627\u0644\u0623\u062E\u0637\u0627\u0621 \u0627\u0644\u062A\u0627\u0644\u064A\u0629", hi: "\u0905\u0917\u0932\u0940 \u0924\u094D\u0930\u0941\u091F\u093F\u092F\u093E\u0901 \u0938\u092E\u091D\u093E\u090F\u0901" },
  // ── sql: the generated-SQL result block ──────────────────────────────────
  "sql.schemaMatch": { en: "Schema Match", fr: "Correspondance de sch\xE9ma", ar: "\u062A\u0637\u0627\u0628\u0642 \u0627\u0644\u0645\u062E\u0637\u0637", hi: "\u0938\u094D\u0915\u0940\u092E\u093E \u092E\u093F\u0932\u093E\u0928" },
  "sql.generatedSql": { en: "Generated SQL", fr: "SQL g\xE9n\xE9r\xE9", ar: "SQL \u0627\u0644\u0645\u064F\u0646\u0634\u0623", hi: "\u091C\u0928\u0930\u0947\u091F \u0915\u093F\u092F\u093E \u0917\u092F\u093E SQL" },
  "sql.queryResults": { en: "Query Results", fr: "R\xE9sultats de la requ\xEAte", ar: "\u0646\u062A\u0627\u0626\u062C \u0627\u0644\u0627\u0633\u062A\u0639\u0644\u0627\u0645", hi: "\u0915\u094D\u0935\u0947\u0930\u0940 \u092A\u0930\u093F\u0923\u093E\u092E" },
  "sql.noRowsReturned": { en: "No rows returned.", fr: "Aucune ligne renvoy\xE9e.", ar: "\u0644\u0645 \u062A\u064F\u0631\u062C\u0639 \u0623\u064A \u0635\u0641\u0648\u0641.", hi: "\u0915\u094B\u0908 \u092A\u0902\u0915\u094D\u0924\u093F \u0928\u0939\u0940\u0902 \u0932\u094C\u091F\u0940\u0964" },
  "sql.needMoreDetail": { en: "Need more detail:", fr: "Plus de d\xE9tails n\xE9cessaires :", ar: "\u0645\u0637\u0644\u0648\u0628 \u0645\u0632\u064A\u062F \u0645\u0646 \u0627\u0644\u062A\u0641\u0627\u0635\u064A\u0644:", hi: "\u0905\u0927\u093F\u0915 \u0935\u093F\u0935\u0930\u0923 \u0906\u0935\u0936\u094D\u092F\u0915:" },
  "sql.noMatches": { en: "No matches", fr: "Aucune correspondance", ar: "\u0644\u0627 \u062A\u0648\u062C\u062F \u0645\u0637\u0627\u0628\u0642\u0627\u062A", hi: "\u0915\u094B\u0908 \u092E\u093F\u0932\u093E\u0928 \u0928\u0939\u0940\u0902" },
  // ── errors: validation-error panels and their tables ─────────────────────
  "errors.howToFix": { en: "How to fix", fr: "Comment corriger", ar: "\u0643\u064A\u0641\u064A\u0629 \u0627\u0644\u0625\u0635\u0644\u0627\u062D", hi: "\u0915\u0948\u0938\u0947 \u0920\u0940\u0915 \u0915\u0930\u0947\u0902" },
  "errors.dimensionalTitle": { en: "Dimensional Validation Errors", fr: "Erreurs de validation dimensionnelle", ar: "\u0623\u062E\u0637\u0627\u0621 \u0627\u0644\u062A\u062D\u0642\u0642 \u0627\u0644\u0628\u064F\u0639\u062F\u064A", hi: "\u0906\u092F\u093E\u092E\u0940 \u0938\u0924\u094D\u092F\u093E\u092A\u0928 \u0924\u094D\u0930\u0941\u091F\u093F\u092F\u093E\u0901" },
  "errors.columns.dbTableName": { en: "Table/Sheet Name", fr: "Nom de table/feuille", ar: "\u0627\u0633\u0645 \u0627\u0644\u062C\u062F\u0648\u0644/\u0627\u0644\u0648\u0631\u0642\u0629", hi: "\u0924\u093E\u0932\u093F\u0915\u093E/\u0936\u0940\u091F \u0928\u093E\u092E" },
  "errors.columns.rowLabel": { en: "Row", fr: "Ligne", ar: "\u0627\u0644\u0635\u0641", hi: "\u092A\u0902\u0915\u094D\u0924\u093F" },
  "errors.columns.rowLabels": { en: "Row Label(s)", fr: "Libell\xE9(s) de ligne", ar: "\u062A\u0633\u0645\u064A\u0629/\u062A\u0633\u0645\u064A\u0627\u062A \u0627\u0644\u0635\u0641", hi: "\u092A\u0902\u0915\u094D\u0924\u093F \u0932\u0947\u092C\u0932" },
  "errors.columns.cellCode": { en: "Cell Code", fr: "Code de cellule", ar: "\u0631\u0645\u0632 \u0627\u0644\u062E\u0644\u064A\u0629", hi: "\u0938\u0947\u0932 \u0915\u094B\u0921" },
  "errors.columns.context": { en: "Context", fr: "Contexte", ar: "\u0627\u0644\u0633\u064A\u0627\u0642", hi: "\u0938\u0902\u0926\u0930\u094D\u092D" },
  "errors.columns.error": { en: "Error", fr: "Erreur", ar: "\u0627\u0644\u062E\u0637\u0623", hi: "\u0924\u094D\u0930\u0941\u091F\u093F" },
  "errors.columns.explanation": { en: "Explanation", fr: "Explication", ar: "\u0627\u0644\u0634\u0631\u062D", hi: "\u0938\u094D\u092A\u0937\u094D\u091F\u0940\u0915\u0930\u0923" },
  "errors.columns.item": { en: "Item", fr: "\xC9l\xE9ment", ar: "\u0627\u0644\u0639\u0646\u0635\u0631", hi: "\u092E\u0926" },
  "errors.columns.expected": { en: "Expected", fr: "Attendu", ar: "\u0627\u0644\u0645\u062A\u0648\u0642\u0639", hi: "\u0905\u092A\u0947\u0915\u094D\u0937\u093F\u0924" },
  "errors.columns.actual": { en: "Actual", fr: "R\xE9el", ar: "\u0627\u0644\u0641\u0639\u0644\u064A", hi: "\u0935\u093E\u0938\u094D\u0924\u0935\u093F\u0915" },
  "errors.category.formulaError": { en: "Formula Error", fr: "Erreur de formule", ar: "\u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u0635\u064A\u063A\u0629", hi: "\u0938\u0942\u0924\u094D\u0930 \u0924\u094D\u0930\u0941\u091F\u093F" },
  "errors.category.qualityCheck": { en: "Quality Check", fr: "Contr\xF4le qualit\xE9", ar: "\u0641\u062D\u0635 \u0627\u0644\u062C\u0648\u062F\u0629", hi: "\u0917\u0941\u0923\u0935\u0924\u094D\u0924\u093E \u091C\u093E\u0901\u091A" },
  "errors.category.specificationError": { en: "Specification Error", fr: "Erreur de sp\xE9cification", ar: "\u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u0645\u0648\u0627\u0635\u0641\u0627\u062A", hi: "\u0935\u093F\u0928\u093F\u0930\u094D\u0926\u0947\u0936 \u0924\u094D\u0930\u0941\u091F\u093F" },
  "errors.category.schemaError": { en: "Schema Error", fr: "Erreur de sch\xE9ma", ar: "\u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u0645\u062E\u0637\u0637", hi: "\u0938\u094D\u0915\u0940\u092E\u093E \u0924\u094D\u0930\u0941\u091F\u093F" },
  "errors.category.dimensionalError": { en: "Dimensional Error", fr: "Erreur dimensionnelle", ar: "\u062E\u0637\u0623 \u0628\u064F\u0639\u062F\u064A", hi: "\u0906\u092F\u093E\u092E\u0940 \u0924\u094D\u0930\u0941\u091F\u093F" },
  "errors.category.validationError": { en: "Validation Error", fr: "Erreur de validation", ar: "\u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u062A\u062D\u0642\u0642", hi: "\u0938\u0924\u094D\u092F\u093E\u092A\u0928 \u0924\u094D\u0930\u0941\u091F\u093F" },
  "errors.category.formulaErrors": { en: "Formula Errors", fr: "Erreurs de formule", ar: "\u0623\u062E\u0637\u0627\u0621 \u0627\u0644\u0635\u064A\u063A\u0629", hi: "\u0938\u0942\u0924\u094D\u0930 \u0924\u094D\u0930\u0941\u091F\u093F\u092F\u093E\u0901" },
  "errors.category.schemaErrors": { en: "Schema Errors", fr: "Erreurs de sch\xE9ma", ar: "\u0623\u062E\u0637\u0627\u0621 \u0627\u0644\u0645\u062E\u0637\u0637", hi: "\u0938\u094D\u0915\u0940\u092E\u093E \u0924\u094D\u0930\u0941\u091F\u093F\u092F\u093E\u0901" },
  "errors.category.dimensionErrors": { en: "Dimension Errors", fr: "Erreurs de dimension", ar: "\u0623\u062E\u0637\u0627\u0621 \u0627\u0644\u0623\u0628\u0639\u0627\u062F", hi: "\u0906\u092F\u093E\u092E \u0924\u094D\u0930\u0941\u091F\u093F\u092F\u093E\u0901" },
  "errors.severity.critical": { en: "Critical", fr: "Critique", ar: "\u062D\u0631\u062C", hi: "\u0917\u0902\u092D\u0940\u0930" },
  "errors.severity.high": { en: "High", fr: "\xC9lev\xE9", ar: "\u0645\u0631\u062A\u0641\u0639", hi: "\u0909\u091A\u094D\u091A" },
  "errors.severity.medium": { en: "Medium", fr: "Moyen", ar: "\u0645\u062A\u0648\u0633\u0637", hi: "\u092E\u0927\u094D\u092F\u092E" },
  // ── feedback ─────────────────────────────────────────────────────────────
  "feedback.thanksPositive": { en: "Great! Glad I could help. \u{1F60A}", fr: "Parfait ! Ravi d\u2019avoir pu aider. \u{1F60A}", ar: "\u0631\u0627\u0626\u0639! \u0633\u0639\u064A\u062F \u0628\u0623\u0646\u0646\u064A \u0627\u0633\u062A\u0637\u0639\u062A \u0627\u0644\u0645\u0633\u0627\u0639\u062F\u0629. \u{1F60A}", hi: "\u092C\u0922\u093C\u093F\u092F\u093E! \u0916\u0941\u0936\u0940 \u0939\u0948 \u0915\u093F \u092E\u0948\u0902 \u092E\u0926\u0926 \u0915\u0930 \u0938\u0915\u093E\u0964 \u{1F60A}" },
  "feedback.sorryNegative": { en: "I\u2019m sorry the experience wasn\u2019t helpful.", fr: "Je suis d\xE9sol\xE9 que cela n\u2019ait pas \xE9t\xE9 utile.", ar: "\u064A\u0624\u0633\u0641\u0646\u064A \u0623\u0646 \u0627\u0644\u062A\u062C\u0631\u0628\u0629 \u0644\u0645 \u062A\u0643\u0646 \u0645\u0641\u064A\u062F\u0629.", hi: "\u0916\u0947\u0926 \u0939\u0948 \u0915\u093F \u092F\u0939 \u0905\u0928\u0941\u092D\u0935 \u0938\u0939\u093E\u092F\u0915 \u0928\u0939\u0940\u0902 \u0930\u0939\u093E\u0964" },
  // ── voice input ──────────────────────────────────────────────────────────
  "voice.start": { en: "Start voice input", fr: "D\xE9marrer la saisie vocale", ar: "\u0628\u062F\u0621 \u0627\u0644\u0625\u062F\u062E\u0627\u0644 \u0627\u0644\u0635\u0648\u062A\u064A", hi: "\u0935\u0949\u0907\u0938 \u0907\u0928\u092A\u0941\u091F \u0936\u0941\u0930\u0942 \u0915\u0930\u0947\u0902" },
  "voice.stop": { en: "Stop recording", fr: "Arr\xEAter l\u2019enregistrement", ar: "\u0625\u064A\u0642\u0627\u0641 \u0627\u0644\u062A\u0633\u062C\u064A\u0644", hi: "\u0930\u093F\u0915\u0949\u0930\u094D\u0921\u093F\u0902\u0917 \u0930\u094B\u0915\u0947\u0902" },
  "voice.transcribing": { en: "Transcribing\u2026", fr: "Transcription\u2026", ar: "\u062C\u0627\u0631\u064D \u0627\u0644\u062A\u0641\u0631\u064A\u063A\u2026", hi: "\u091F\u094D\u0930\u093E\u0902\u0938\u0915\u094D\u0930\u093E\u0907\u092C \u0939\u094B \u0930\u0939\u093E \u0939\u0948\u2026" },
  "voice.stopTranscribing": { en: "Stop transcribing", fr: "Arr\xEAter la transcription", ar: "\u0625\u064A\u0642\u0627\u0641 \u0627\u0644\u062A\u0641\u0631\u064A\u063A", hi: "\u091F\u094D\u0930\u093E\u0902\u0938\u0915\u094D\u0930\u093F\u092A\u094D\u0936\u0928 \u0930\u094B\u0915\u0947\u0902" },
  "voice.speakNow": { en: "Speak now\u2026", fr: "Parlez maintenant\u2026", ar: "\u062A\u062D\u062F\u0651\u062B \u0627\u0644\u0622\u0646\u2026", hi: "\u0905\u092C \u092C\u094B\u0932\u0947\u0902\u2026" }
};

// src/i18n.js
import { createContext, useContext } from "react";
var RTL_LANGUAGES = /* @__PURE__ */ new Set(["ar"]);
var ACTIONS = {
  "Check report status": {
    en: "Check report status",
    fr: "V\xE9rifier le statut du rapport",
    ar: "\u0627\u0644\u062A\u062D\u0642\u0642 \u0645\u0646 \u062D\u0627\u0644\u0629 \u0627\u0644\u062A\u0642\u0631\u064A\u0631",
    hi: "\u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0915\u0940 \u0938\u094D\u0925\u093F\u0924\u093F \u091C\u093E\u0902\u091A\u0947\u0902"
  },
  "Generate instance for a report": {
    en: "Generate instance for a report",
    fr: "G\xE9n\xE9rer une instance de rapport",
    ar: "\u0625\u0646\u0634\u0627\u0621 \u0646\u0633\u062E\u0629 \u0644\u062A\u0642\u0631\u064A\u0631",
    hi: "\u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0915\u0947 \u0932\u093F\u090F \u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 \u092C\u0928\u093E\u090F\u0901"
  },
  "Schedule a report": {
    en: "Schedule a report",
    fr: "Planifier un rapport",
    ar: "\u062C\u062F\u0648\u0644\u0629 \u062A\u0642\u0631\u064A\u0631",
    hi: "\u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0936\u0947\u0921\u094D\u092F\u0942\u0932 \u0915\u0930\u0947\u0902"
  },
  "Perform comparative analysis": {
    en: "Perform comparative analysis",
    fr: "Effectuer une analyse comparative",
    ar: "\u0625\u062C\u0631\u0627\u0621 \u062A\u062D\u0644\u064A\u0644 \u0645\u0642\u0627\u0631\u0646",
    hi: "\u0924\u0941\u0932\u0928\u093E\u0924\u094D\u092E\u0915 \u0935\u093F\u0936\u094D\u0932\u0947\u0937\u0923 \u0915\u0930\u0947\u0902"
  },
  "Retrieve data from database": {
    en: "Retrieve data from database",
    fr: "Extraire des donn\xE9es de la base de donn\xE9es",
    ar: "\u0627\u0633\u062A\u0631\u062C\u0627\u0639 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A \u0645\u0646 \u0642\u0627\u0639\u062F\u0629 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A",
    hi: "\u0921\u0947\u091F\u093E\u092C\u0947\u0938 \u0938\u0947 \u0921\u0947\u091F\u093E \u092A\u094D\u0930\u093E\u092A\u094D\u0924 \u0915\u0930\u0947\u0902"
  }
};
var ACTION_DESCRIPTIONS = {
  "Check report status": {
    en: "Look up the latest status of any report",
    fr: "Consulter le dernier statut de n\u2019importe quel rapport",
    ar: "\u0627\u0644\u0627\u0637\u0644\u0627\u0639 \u0639\u0644\u0649 \u0622\u062E\u0631 \u062D\u0627\u0644\u0629 \u0644\u0623\u064A \u062A\u0642\u0631\u064A\u0631",
    hi: "\u0915\u093F\u0938\u0940 \u092D\u0940 \u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0915\u0940 \u0928\u0935\u0940\u0928\u0924\u092E \u0938\u094D\u0925\u093F\u0924\u093F \u0926\u0947\u0916\u0947\u0902"
  },
  "Generate instance for a report": {
    en: "Trigger a new report instance for a period",
    fr: "D\xE9clencher une nouvelle instance de rapport pour une p\xE9riode",
    ar: "\u062A\u0634\u063A\u064A\u0644 \u0646\u0633\u062E\u0629 \u062A\u0642\u0631\u064A\u0631 \u062C\u062F\u064A\u062F\u0629 \u0644\u0641\u062A\u0631\u0629 \u0645\u062D\u062F\u062F\u0629",
    hi: "\u0915\u093F\u0938\u0940 \u0905\u0935\u0927\u093F \u0915\u0947 \u0932\u093F\u090F \u0928\u0908 \u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 \u091A\u0932\u093E\u090F\u0901"
  },
  "Schedule a report": {
    en: "Schedule a report to run at a future date/time",
    fr: "Planifier l\u2019ex\xE9cution d\u2019un rapport \xE0 une date/heure future",
    ar: "\u062C\u062F\u0648\u0644\u0629 \u062A\u0634\u063A\u064A\u0644 \u062A\u0642\u0631\u064A\u0631 \u0641\u064A \u062A\u0627\u0631\u064A\u062E/\u0648\u0642\u062A \u0645\u0633\u062A\u0642\u0628\u0644\u064A",
    hi: "\u092D\u0935\u093F\u0937\u094D\u092F \u0915\u0940 \u0924\u093F\u0925\u093F/\u0938\u092E\u092F \u092A\u0930 \u0930\u093F\u092A\u094B\u0930\u094D\u091F \u091A\u0932\u093E\u0928\u0947 \u0915\u0947 \u0932\u093F\u090F \u0936\u0947\u0921\u094D\u092F\u0942\u0932 \u0915\u0930\u0947\u0902"
  },
  "Perform comparative analysis": {
    en: "Compare two report instances period-over-period",
    fr: "Comparer deux instances de rapport d\u2019une p\xE9riode \xE0 l\u2019autre",
    ar: "\u0645\u0642\u0627\u0631\u0646\u0629 \u0646\u0633\u062E\u062A\u064E\u064A \u062A\u0642\u0631\u064A\u0631 \u0628\u064A\u0646 \u0641\u062A\u0631\u062A\u064A\u0646",
    hi: "\u0926\u094B \u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 \u0915\u0940 \u0905\u0935\u0927\u093F-\u0926\u0930-\u0905\u0935\u0927\u093F \u0924\u0941\u0932\u0928\u093E \u0915\u0930\u0947\u0902"
  },
  "Retrieve data from database": {
    en: "Query the database using plain English",
    fr: "Interroger la base de donn\xE9es en langage courant",
    ar: "\u0627\u0644\u0627\u0633\u062A\u0639\u0644\u0627\u0645 \u0639\u0646 \u0642\u0627\u0639\u062F\u0629 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A \u0628\u0644\u063A\u0629 \u0628\u0633\u064A\u0637\u0629",
    hi: "\u0938\u0930\u0932 \u092D\u093E\u0937\u093E \u092E\u0947\u0902 \u0921\u0947\u091F\u093E\u092C\u0947\u0938 \u0938\u0947 \u092A\u0942\u091B\u0947\u0902"
  }
};
var OPTION_LABELS = {
  "Schedule": {
    en: "Schedule",
    fr: "Planifier",
    ar: "\u062C\u062F\u0648\u0644\u0629",
    hi: "\u0936\u0947\u0921\u094D\u092F\u0942\u0932 \u0915\u0930\u0947\u0902"
  },
  "Change Data": {
    en: "Change Data",
    fr: "Modifier les donn\xE9es",
    ar: "\u062A\u063A\u064A\u064A\u0631 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A",
    hi: "\u0921\u0947\u091F\u093E \u092C\u0926\u0932\u0947\u0902"
  },
  "Yes": { en: "Yes", fr: "Oui", ar: "\u0646\u0639\u0645", hi: "\u0939\u093E\u0901" },
  "No": { en: "No", fr: "Non", ar: "\u0644\u0627", hi: "\u0928\u0939\u0940\u0902" }
};
var STRINGS = {
  // ── Welcome card ────────────────────────────────────────────────────────
  welcomeGreeting: {
    en: "\u{1F44B} Hi! I\u2019m your Report Assistant.",
    fr: "\u{1F44B} Bonjour ! Je suis votre assistant de rapports.",
    ar: "\u{1F44B} \u0645\u0631\u062D\u0628\u064B\u0627! \u0623\u0646\u0627 \u0645\u0633\u0627\u0639\u062F \u0627\u0644\u062A\u0642\u0627\u0631\u064A\u0631 \u0627\u0644\u062E\u0627\u0635 \u0628\u0643.",
    hi: "\u{1F44B} \u0928\u092E\u0938\u094D\u0924\u0947! \u092E\u0948\u0902 \u0906\u092A\u0915\u093E \u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0938\u0939\u093E\u092F\u0915 \u0939\u0942\u0901\u0964"
  },
  welcomeHelp: {
    en: "I can help you with:",
    fr: "Je peux vous aider \xE0 :",
    ar: "\u064A\u0645\u0643\u0646\u0646\u064A \u0645\u0633\u0627\u0639\u062F\u062A\u0643 \u0641\u064A:",
    hi: "\u092E\u0948\u0902 \u0906\u092A\u0915\u0940 \u0907\u0928\u092E\u0947\u0902 \u092E\u0926\u0926 \u0915\u0930 \u0938\u0915\u0924\u093E \u0939\u0942\u0901:"
  },
  welcomeItemStatus: {
    en: "Checking the *status* of a report",
    fr: "V\xE9rifier le *statut* d\u2019un rapport",
    ar: "\u0627\u0644\u062A\u062D\u0642\u0642 \u0645\u0646 *\u062D\u0627\u0644\u0629* \u062A\u0642\u0631\u064A\u0631",
    hi: "\u0915\u093F\u0938\u0940 \u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0915\u0940 *\u0938\u094D\u0925\u093F\u0924\u093F* \u091C\u093E\u0902\u091A\u0928\u093E"
  },
  welcomeItemGenerate: {
    en: "*Generating* a new report instance for a date",
    fr: "*G\xE9n\xE9rer* une nouvelle instance de rapport pour une date",
    ar: "*\u0625\u0646\u0634\u0627\u0621* \u0646\u0633\u062E\u0629 \u062A\u0642\u0631\u064A\u0631 \u062C\u062F\u064A\u062F\u0629 \u0644\u062A\u0627\u0631\u064A\u062E \u0645\u062D\u062F\u062F",
    hi: "\u0915\u093F\u0938\u0940 \u0924\u093F\u0925\u093F \u0915\u0947 \u0932\u093F\u090F \u0928\u0908 \u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 *\u092C\u0928\u093E\u0928\u093E*"
  },
  welcomeItemSchedule: {
    en: "*Scheduling* reports for a future date and time",
    fr: "*Planifier* des rapports pour une date et une heure futures",
    ar: "*\u062C\u062F\u0648\u0644\u0629* \u0627\u0644\u062A\u0642\u0627\u0631\u064A\u0631 \u0644\u062A\u0627\u0631\u064A\u062E \u0648\u0648\u0642\u062A \u0645\u0633\u062A\u0642\u0628\u0644\u064A\u064A\u0646",
    hi: "\u092D\u0935\u093F\u0937\u094D\u092F \u0915\u0940 \u0924\u093F\u0925\u093F \u0914\u0930 \u0938\u092E\u092F \u0915\u0947 \u0932\u093F\u090F \u0930\u093F\u092A\u094B\u0930\u094D\u091F *\u0936\u0947\u0921\u094D\u092F\u0942\u0932* \u0915\u0930\u0928\u093E"
  },
  welcomeItemCompare: {
    en: "Performing *comparative analysis* on report instances",
    fr: "Effectuer une *analyse comparative* sur des instances de rapport",
    ar: "\u0625\u062C\u0631\u0627\u0621 *\u062A\u062D\u0644\u064A\u0644 \u0645\u0642\u0627\u0631\u0646* \u0639\u0644\u0649 \u0646\u0633\u062E \u0627\u0644\u062A\u0642\u0627\u0631\u064A\u0631",
    hi: "\u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 \u092A\u0930 *\u0924\u0941\u0932\u0928\u093E\u0924\u094D\u092E\u0915 \u0935\u093F\u0936\u094D\u0932\u0947\u0937\u0923* \u0915\u0930\u0928\u093E"
  },
  welcomeItemDatabase: {
    en: "Retrieving data from the *database*",
    fr: "Extraire des donn\xE9es de la *base de donn\xE9es*",
    ar: "\u0627\u0633\u062A\u0631\u062C\u0627\u0639 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A \u0645\u0646 *\u0642\u0627\u0639\u062F\u0629 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A*",
    hi: "*\u0921\u0947\u091F\u093E\u092C\u0947\u0938* \u0938\u0947 \u0921\u0947\u091F\u093E \u092A\u094D\u0930\u093E\u092A\u094D\u0924 \u0915\u0930\u0928\u093E"
  },
  welcomeItemErrors: {
    en: "*Explaining errors* in a failed report instance",
    fr: "*Expliquer les erreurs* d\u2019une instance de rapport en \xE9chec",
    ar: "*\u0634\u0631\u062D \u0627\u0644\u0623\u062E\u0637\u0627\u0621* \u0641\u064A \u0646\u0633\u062E\u0629 \u062A\u0642\u0631\u064A\u0631 \u0641\u0627\u0634\u0644\u0629",
    hi: "\u0935\u093F\u092B\u0932 \u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0907\u0902\u0938\u094D\u091F\u0947\u0902\u0938 \u092E\u0947\u0902 *\u0924\u094D\u0930\u0941\u091F\u093F\u092F\u093E\u0901 \u0938\u092E\u091D\u093E\u0928\u093E*"
  },
  welcomeCta: {
    en: "Click a category to use guided mode, or type freely:",
    fr: "Cliquez sur une cat\xE9gorie pour le mode guid\xE9, ou \xE9crivez librement :",
    ar: "\u0627\u0646\u0642\u0631 \u0639\u0644\u0649 \u0641\u0626\u0629 \u0644\u0627\u0633\u062A\u062E\u062F\u0627\u0645 \u0627\u0644\u0648\u0636\u0639 \u0627\u0644\u0645\u0648\u062C\u0651\u0647\u060C \u0623\u0648 \u0627\u0643\u062A\u0628 \u0628\u062D\u0631\u064A\u0629:",
    hi: "\u0917\u093E\u0907\u0921\u0947\u0921 \u092E\u094B\u0921 \u0915\u0947 \u0932\u093F\u090F \u0915\u093F\u0938\u0940 \u0936\u094D\u0930\u0947\u0923\u0940 \u092A\u0930 \u0915\u094D\u0932\u093F\u0915 \u0915\u0930\u0947\u0902, \u092F\u093E \u0938\u094D\u0935\u0924\u0902\u0924\u094D\u0930 \u0930\u0942\u092A \u0938\u0947 \u0932\u093F\u0916\u0947\u0902:"
  },
  // ── Menus ───────────────────────────────────────────────────────────────
  actionMenuPrompt: {
    en: "What would you like to do next?",
    fr: "Que souhaitez-vous faire ensuite ?",
    ar: "\u0645\u0627\u0630\u0627 \u062A\u0631\u064A\u062F \u0623\u0646 \u062A\u0641\u0639\u0644 \u0628\u0639\u062F \u0630\u0644\u0643\u061F",
    hi: "\u0906\u092A \u0906\u0917\u0947 \u0915\u094D\u092F\u093E \u0915\u0930\u0928\u093E \u091A\u093E\u0939\u0947\u0902\u0917\u0947?"
  },
  startGuidedFlow: {
    en: "Start guided flow",
    fr: "D\xE9marrer le mode guid\xE9",
    ar: "\u0628\u062F\u0621 \u0627\u0644\u0648\u0636\u0639 \u0627\u0644\u0645\u0648\u062C\u0651\u0647",
    hi: "\u0917\u093E\u0907\u0921\u0947\u0921 \u092E\u094B\u0921 \u0936\u0941\u0930\u0942 \u0915\u0930\u0947\u0902"
  },
  guidedBadge: {
    en: "\u{1F9ED} Guided",
    fr: "\u{1F9ED} Guid\xE9",
    ar: "\u{1F9ED} \u0645\u0648\u062C\u0651\u0647",
    hi: "\u{1F9ED} \u0917\u093E\u0907\u0921\u0947\u0921"
  },
  guidedModeIndicator: {
    en: "\u{1F9ED} Guided mode \u2014 answer the question above",
    fr: "\u{1F9ED} Mode guid\xE9 \u2014 r\xE9pondez \xE0 la question ci-dessus",
    ar: "\u{1F9ED} \u0627\u0644\u0648\u0636\u0639 \u0627\u0644\u0645\u0648\u062C\u0651\u0647 \u2014 \u0623\u062C\u0628 \u0639\u0646 \u0627\u0644\u0633\u0624\u0627\u0644 \u0623\u0639\u0644\u0627\u0647",
    hi: "\u{1F9ED} \u0917\u093E\u0907\u0921\u0947\u0921 \u092E\u094B\u0921 \u2014 \u090A\u092A\u0930 \u0926\u093F\u090F \u0917\u090F \u092A\u094D\u0930\u0936\u094D\u0928 \u0915\u093E \u0909\u0924\u094D\u0924\u0930 \u0926\u0947\u0902"
  },
  // ── Input bar ───────────────────────────────────────────────────────────
  inputPlaceholder: {
    en: "Ask about a report\u2026 or press the mic",
    fr: "Posez une question sur un rapport\u2026 ou appuyez sur le micro",
    ar: "\u0627\u0633\u0623\u0644 \u0639\u0646 \u062A\u0642\u0631\u064A\u0631\u2026 \u0623\u0648 \u0627\u0636\u063A\u0637 \u0639\u0644\u0649 \u0627\u0644\u0645\u064A\u0643\u0631\u0648\u0641\u0648\u0646",
    hi: "\u0915\u093F\u0938\u0940 \u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0915\u0947 \u092C\u093E\u0930\u0947 \u092E\u0947\u0902 \u092A\u0942\u091B\u0947\u0902\u2026 \u092F\u093E \u092E\u093E\u0907\u0915 \u0926\u092C\u093E\u090F\u0901"
  },
  inputPlaceholderGuided: {
    en: "Type your answer\u2026",
    fr: "Saisissez votre r\xE9ponse\u2026",
    ar: "\u0627\u0643\u062A\u0628 \u0625\u062C\u0627\u0628\u062A\u0643\u2026",
    hi: "\u0905\u092A\u0928\u093E \u0909\u0924\u094D\u0924\u0930 \u0932\u093F\u0916\u0947\u0902\u2026"
  },
  clearChat: {
    en: "Clear chat history",
    fr: "Effacer l\u2019historique de la conversation",
    ar: "\u0645\u0633\u062D \u0633\u062C\u0644 \u0627\u0644\u0645\u062D\u0627\u062F\u062B\u0629",
    hi: "\u091A\u0948\u091F \u0907\u0924\u093F\u0939\u093E\u0938 \u0938\u093E\u092B\u093C \u0915\u0930\u0947\u0902"
  },
  stopGenerating: {
    en: "Stop generating",
    fr: "Arr\xEAter la g\xE9n\xE9ration",
    ar: "\u0625\u064A\u0642\u0627\u0641 \u0627\u0644\u062A\u0648\u0644\u064A\u062F",
    hi: "\u091C\u0928\u0930\u0947\u0936\u0928 \u0930\u094B\u0915\u0947\u0902"
  },
  sendMessage: {
    en: "Send message",
    fr: "Envoyer le message",
    ar: "\u0625\u0631\u0633\u0627\u0644 \u0627\u0644\u0631\u0633\u0627\u0644\u0629",
    hi: "\u0938\u0902\u0926\u0947\u0936 \u092D\u0947\u091C\u0947\u0902"
  },
  chatLanguage: {
    en: "Chat language",
    fr: "Langue de la conversation",
    ar: "\u0644\u063A\u0629 \u0627\u0644\u0645\u062D\u0627\u062F\u062B\u0629",
    hi: "\u091A\u0948\u091F \u0915\u0940 \u092D\u093E\u0937\u093E"
  },
  // ── Fixed status / error messages ───────────────────────────────────────
  errorGeneric: {
    en: "Something went wrong. Please try again.",
    fr: "Une erreur s\u2019est produite. Veuillez r\xE9essayer.",
    ar: "\u062D\u062F\u062B \u062E\u0637\u0623 \u0645\u0627. \u064A\u0631\u062C\u0649 \u0627\u0644\u0645\u062D\u0627\u0648\u0644\u0629 \u0645\u0631\u0629 \u0623\u062E\u0631\u0649.",
    hi: "\u0915\u0941\u091B \u0917\u0932\u0924 \u0939\u094B \u0917\u092F\u093E. \u0915\u0943\u092A\u092F\u093E \u092A\u0941\u0928\u0903 \u092A\u094D\u0930\u092F\u093E\u0938 \u0915\u0930\u0947\u0902."
  },
  errorComparison: {
    en: "Comparison failed. Please try again.",
    fr: "La comparaison a \xE9chou\xE9. Veuillez r\xE9essayer.",
    ar: "\u0641\u0634\u0644\u062A \u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0629. \u064A\u0631\u062C\u0649 \u0627\u0644\u0645\u062D\u0627\u0648\u0644\u0629 \u0645\u0631\u0629 \u0623\u062E\u0631\u0649.",
    hi: "\u0924\u0941\u0932\u0928\u093E \u0935\u093F\u092B\u0932 \u0930\u0939\u0940. \u0915\u0943\u092A\u092F\u093E \u092A\u0941\u0928\u0903 \u092A\u094D\u0930\u092F\u093E\u0938 \u0915\u0930\u0947\u0902."
  },
  errorExplanations: {
    en: "Failed to generate explanations. Please try again.",
    fr: "\xC9chec de la g\xE9n\xE9ration des explications. Veuillez r\xE9essayer.",
    ar: "\u062A\u0639\u0630\u0651\u0631 \u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u062A\u0641\u0633\u064A\u0631\u0627\u062A. \u064A\u0631\u062C\u0649 \u0627\u0644\u0645\u062D\u0627\u0648\u0644\u0629 \u0645\u0631\u0629 \u0623\u062E\u0631\u0649.",
    hi: "\u0938\u094D\u092A\u0937\u094D\u091F\u0940\u0915\u0930\u0923 \u092C\u0928\u093E\u0928\u0947 \u092E\u0947\u0902 \u0935\u093F\u092B\u0932. \u0915\u0943\u092A\u092F\u093E \u092A\u0941\u0928\u0903 \u092A\u094D\u0930\u092F\u093E\u0938 \u0915\u0930\u0947\u0902."
  },
  noDataFound: {
    en: "No data found.",
    fr: "Aucune donn\xE9e trouv\xE9e.",
    ar: "\u0644\u0645 \u064A\u062A\u0645 \u0627\u0644\u0639\u062B\u0648\u0631 \u0639\u0644\u0649 \u0628\u064A\u0627\u0646\u0627\u062A.",
    hi: "\u0915\u094B\u0908 \u0921\u0947\u091F\u093E \u0928\u0939\u0940\u0902 \u092E\u093F\u0932\u093E."
  },
  wasThisHelpful: {
    en: "Was this helpful?",
    fr: "Cette r\xE9ponse vous a-t-elle \xE9t\xE9 utile ?",
    ar: "\u0647\u0644 \u0643\u0627\u0646 \u0647\u0630\u0627 \u0645\u0641\u064A\u062F\u064B\u0627\u061F",
    hi: "\u0915\u094D\u092F\u093E \u092F\u0939 \u0938\u0939\u093E\u092F\u0915 \u0925\u093E?"
  },
  // ── Pickers / tables ────────────────────────────────────────────────────
  selectReportName: {
    en: "Select Report Name",
    fr: "S\xE9lectionner le nom du rapport",
    ar: "\u0627\u062E\u062A\u0631 \u0627\u0633\u0645 \u0627\u0644\u062A\u0642\u0631\u064A\u0631",
    hi: "\u0930\u093F\u092A\u094B\u0930\u094D\u091F \u0915\u093E \u0928\u093E\u092E \u091A\u0941\u0928\u0947\u0902"
  },
  typeToFilter: {
    en: "Type to filter\u2026",
    fr: "Filtrer\u2026",
    ar: "\u0627\u0643\u062A\u0628 \u0644\u0644\u062A\u0635\u0641\u064A\u0629\u2026",
    hi: "\u092B\u093C\u093F\u0932\u094D\u091F\u0930 \u0915\u0930\u0928\u0947 \u0915\u0947 \u0932\u093F\u090F \u0932\u093F\u0916\u0947\u0902\u2026"
  },
  checkAnotherDate: {
    en: "Would you also like to check status for another reporting date?",
    fr: "Souhaitez-vous aussi v\xE9rifier le statut pour une autre date de d\xE9claration ?",
    ar: "\u0647\u0644 \u062A\u0648\u062F \u0623\u064A\u0636\u064B\u0627 \u0627\u0644\u062A\u062D\u0642\u0642 \u0645\u0646 \u0627\u0644\u062D\u0627\u0644\u0629 \u0644\u062A\u0627\u0631\u064A\u062E \u062A\u0642\u0631\u064A\u0631 \u0622\u062E\u0631\u061F",
    hi: "\u0915\u094D\u092F\u093E \u0906\u092A \u0915\u093F\u0938\u0940 \u0905\u0928\u094D\u092F \u0930\u093F\u092A\u094B\u0930\u094D\u091F\u093F\u0902\u0917 \u0924\u093F\u0925\u093F \u0915\u0947 \u0932\u093F\u090F \u092D\u0940 \u0938\u094D\u0925\u093F\u0924\u093F \u091C\u093E\u0902\u091A\u0928\u093E \u091A\u093E\u0939\u0947\u0902\u0917\u0947?"
  },
  prev: { en: "Prev", fr: "Pr\xE9c.", ar: "\u0627\u0644\u0633\u0627\u0628\u0642", hi: "\u092A\u093F\u091B\u0932\u093E" },
  next: { en: "Next", fr: "Suiv.", ar: "\u0627\u0644\u062A\u0627\u0644\u064A", hi: "\u0905\u0917\u0932\u093E" },
  records: { en: "records", fr: "enregistrements", ar: "\u0633\u062C\u0644\u0627\u062A", hi: "\u0930\u093F\u0915\u0949\u0930\u094D\u0921" }
};
var FALLBACK = "en";
function translate(dict, key, lang) {
  const entry = dict[key];
  if (!entry) return key;
  return entry[lang] ?? entry[FALLBACK] ?? key;
}
function makeT(lang) {
  const t = (key) => key in STRINGS ? translate(STRINGS, key, lang) : translate(UI, key, lang);
  t.action = (englishToken) => translate(ACTIONS, englishToken, lang);
  t.actionDesc = (englishToken) => translate(ACTION_DESCRIPTIONS, englishToken, lang);
  t.option = (englishValue) => translate(OPTION_LABELS, englishValue, lang);
  t.echo = (value) => {
    if (value in ACTIONS) return translate(ACTIONS, value, lang);
    if (value in OPTION_LABELS) return translate(OPTION_LABELS, value, lang);
    return value;
  };
  t.lang = lang;
  t.dir = RTL_LANGUAGES.has(lang) ? "rtl" : "ltr";
  return t;
}
function isRtl(lang) {
  return RTL_LANGUAGES.has(lang);
}
var LanguageContext = createContext(FALLBACK);
function useT() {
  return makeT(useContext(LanguageContext));
}

// src/components/VarianceChartModal.jsx
import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
  LabelList
} from "recharts";
var COLOR_A = "#60A5FA";
var COLOR_B = "#A78BFA";
var COLOR_SIGN = "#D97706";
var COLOR_POS = "#16A34A";
var COLOR_NEG = "#DC2626";
var COLOR_FLAT = "#6B7280";
function fmtFinancial(v) {
  if (v === null || v === void 0) return "\u2014";
  if (v === 0) return "0";
  const abs = Math.abs(v);
  if (abs >= 1e12) return `${(v / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(v / 1e3).toFixed(2)}K`;
  if (abs >= 1) return v.toFixed(2);
  if (abs >= 1e-3) return v.toFixed(4);
  const places = Math.min(10, Math.max(4, Math.ceil(-Math.log10(abs)) + 3));
  return v.toFixed(places);
}
function fmtRaw(v) {
  if (v === null || v === void 0) return "\u2014";
  return Number(v).toLocaleString(void 0, { maximumFractionDigits: 6 });
}
function VarTooltip({ active, payload, label, labelA, labelB }) {
  const t = useT();
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload ?? {};
  const pct = row.pct_change;
  return /* @__PURE__ */ h("div", { className: "vc-tooltip" }, /* @__PURE__ */ h("div", { className: "vc-tooltip-title" }, row.fullName || label), payload.map((p) => {
    const rawVal = row[p.dataKey.replace("_log", "")] ?? p.value;
    return /* @__PURE__ */ h("div", { key: p.dataKey, className: "vc-tooltip-row" }, /* @__PURE__ */ h("span", { className: "vc-tooltip-dot", style: { background: p.color } }), /* @__PURE__ */ h("span", { className: "vc-tooltip-key" }, p.name, ":"), /* @__PURE__ */ h("span", { className: "vc-tooltip-val" }, fmtFinancial(rawVal)));
  }), row[labelA] !== void 0 && /* @__PURE__ */ h("div", { className: "vc-tooltip-raw" }, "Raw ", labelA, ": ", fmtRaw(row[labelA])), row[labelB] !== void 0 && /* @__PURE__ */ h("div", { className: "vc-tooltip-raw" }, "Raw ", labelB, ": ", fmtRaw(row[labelB])), row.unit && /* @__PURE__ */ h("div", { className: "vc-tooltip-raw" }, "Unit: ", row.unit), pct !== void 0 && pct !== null && /* @__PURE__ */ h(
    "div",
    {
      className: "vc-tooltip-pct",
      style: { color: pct > 0 ? COLOR_POS : pct < 0 ? COLOR_NEG : COLOR_FLAT }
    },
    /* @__PURE__ */ h("span", { className: "vc-tip-dot", "aria-hidden": "true" }),
    fmtChange(pct, t),
    " ",
    pct > 0 ? t("comparativeAnalysis.legendIncrease").toLowerCase() : pct < 0 ? t("comparativeAnalysis.legendDecrease").toLowerCase() : t("comparativeAnalysis.legendNoChange").toLowerCase()
  ), (row.pct_change === null || row.pct_change === void 0) && /* @__PURE__ */ h("div", { className: "vc-tooltip-zero" }, t("comparativeAnalysis.zeroPreviousNote")), row.sign_change && /* @__PURE__ */ h("div", { className: "vc-tooltip-sign" }, "\u21D5 ", t("comparativeAnalysis.directionReversed")), row.anomaly_flags?.length > 0 && /* @__PURE__ */ h("div", { className: "vc-tooltip-anomaly" }, row.anomaly_flags.join(" \xB7 ")));
}
function fmtAxis(v) {
  const abs = Math.abs(v);
  if (abs >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
  if (abs >= 1e-3 || abs === 0) return String(v);
  const places = Math.min(8, Math.ceil(-Math.log10(abs)) + 2);
  return v.toFixed(places);
}
function signedLog(v) {
  if (v === null || v === void 0 || v === 0) return 0;
  return Math.sign(v) * Math.log10(Math.abs(v) + 1);
}
function fmtLogAxis(logV) {
  if (logV === 0) return "0";
  const sign = logV < 0 ? "-" : "";
  const raw = Math.sign(logV) * (Math.pow(10, Math.abs(logV)) - 1);
  return sign + fmtAxis(Math.abs(raw));
}
function shortLabel(str, max = 14) {
  if (!str) return "";
  const base = str.includes(" [") ? str.slice(0, str.indexOf(" [")) : str;
  return base.length > max ? base.slice(0, max - 1) + "\u2026" : base;
}
function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
function fmtChange(v, t) {
  if (v === null || v === void 0) return t("common.notAvailable");
  const abs = Math.abs(v);
  const sign = v > 0 ? "+" : v < 0 ? "-" : "";
  if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(2)}B%`;
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(2)}M%`;
  if (abs >= 1e3) return `${sign}${Math.round(abs).toLocaleString()}%`;
  return `${sign}${abs.toFixed(2)}%`;
}
function buildStandaloneHtml({ rows, meta, labelA, labelB, reportName, summaryText, lang = "en" }) {
  const t = makeT(lang);
  const generated = (/* @__PURE__ */ new Date()).toLocaleString();
  const total = rows.length;
  const inc = rows.filter((r) => (r.diff ?? 0) > 0).length;
  const dec = rows.filter((r) => (r.diff ?? 0) < 0).length;
  const flat = total - inc - dec;
  const criticalRows = rows.filter(
    (r) => r.importance_matched && r.importance_tier === "Critical"
  );
  const headlineRows = rows.filter(
    (r) => r.importance_matched && (r.importance_tier === "Critical" || r.importance_tier === "High")
  );
  const graphRows = criticalRows.length ? criticalRows : rows;
  const graphIsCritical = criticalRows.length > 0;
  const analysisHtml = (() => {
    const raw = String(summaryText || "").replace(/^AI\s+Summary:\s*/i, "").trim();
    if (!raw) return "";
    const items = raw.split("\n").map((l) => l.replace(/^[•\-*]\s*/, "").trim()).filter(Boolean).map((l) => escapeHtml(l).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>"));
    if (!items.length) return "";
    return `<section class="ai">
<h2>${t("comparativeAnalysis.aiAnalysis")}</h2>
<p class="aisub">Generated from the ${headlineRows.length.toLocaleString()} Critical and High
regulatory-importance concept(s) in this comparison.</p>
<ul>${items.map((i) => `<li>${i}</li>`).join("")}</ul>
</section>`;
  })();
  const ROW_H = 26, PAD_L = 300, PAD_R = 150, W = 1180;
  const bodyH = Math.max(1, graphRows.length) * ROW_H;
  const scale = graphRows.reduce(
    (m, r) => Math.max(m, Math.abs(r.val_a ?? 0), Math.abs(r.val_b ?? 0)),
    0
  ) || 1;
  const TRACK = W - PAD_L - PAD_R;
  const logMax = Math.abs(signedLog(scale)) || 1;
  const barW = (v) => Math.max(3, Math.abs(signedLog(v ?? 0)) / logMax * TRACK);
  const bars = graphRows.map((r, i) => {
    const y = i * ROW_H;
    const a = barW(r.val_a), b = barW(r.val_b);
    const pos = (r.diff ?? 0) > 0, neg = (r.diff ?? 0) < 0;
    const dirCol = pos ? "#16A34A" : neg ? "#DC2626" : "#6B7280";
    const arrow = pos ? "\u2191" : neg ? "\u2193" : "\u2192";
    const pct = fmtChange(r.pct_change, t);
    return `<g><title>${escapeHtml(r.concept)}${r.context_key && r.context_key !== "BASE" ? `
Context: ${escapeHtml(r.context_key)}` : ""}
${escapeHtml(labelA)} (${t("comparativeAnalysis.tooltipCurrent")}): ${fmtRaw(r.val_a)}
${escapeHtml(labelB)} (${t("comparativeAnalysis.tooltipPrevious")}): ${fmtRaw(r.val_b)}
${t("comparativeAnalysis.tooltipDifference")}: ${(r.diff ?? 0) > 0 ? "+" : ""}${fmtRaw(r.diff)}
${t("comparativeAnalysis.tooltipChange")}: ${pct} ${arrow}
${t("comparativeAnalysis.tooltipDirection")}: ${pos ? t("comparativeAnalysis.increased") : neg ? t("comparativeAnalysis.decreased") : t("comparativeAnalysis.legendNoChange")}${r.sign_change ? `
${t("comparativeAnalysis.tooltipSignReversal")}` : ""}${r.unit ? `
Unit: ${escapeHtml(r.unit)}` : ""}</title><text x="${PAD_L - 10}" y="${y + 17}" text-anchor="end" class="lbl">${escapeHtml(
      (r.concept || "").length > 46 ? r.concept.slice(0, 45) + "\u2026" : r.concept
    )}</text><rect x="${PAD_L}" y="${y + 4}" width="${a.toFixed(1)}" height="8" fill="${COLOR_A}"/><rect x="${PAD_L}" y="${y + 14}" width="${b.toFixed(1)}" height="8" fill="${COLOR_B}"/><text x="${W - PAD_R + 8}" y="${y + 17}" class="dir" fill="${dirCol}">${arrow} ${pct}</text></g>`;
  }).join("");
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Variance Analysis${reportName ? ` \u2014 ${escapeHtml(reportName)}` : ""}</title>
<style>
:root{--ink:#111827;--muted:#6B7280;--rule:#E5E7EB;--paper:#fff;--sunken:#F9FAFB;
--a:${COLOR_A};--b:${COLOR_B};--up:#16A34A;--down:#DC2626;--flat:#6B7280}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font:14px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:28px 20px 64px}
h1{font-size:1.5rem;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--muted);margin:0 0 18px}
.cmp{display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-bottom:18px}
.key{display:inline-flex;align-items:center;gap:7px;font-weight:600}
.sw{width:14px;height:14px;border-radius:3px;display:inline-block}
.cov{background:var(--sunken);border:1px solid var(--rule);border-left:3px solid var(--a);
padding:12px 16px;margin:0 0 22px;border-radius:3px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 22px}
.stat{border:1px solid var(--rule);border-radius:4px;padding:10px 16px;min-width:104px;background:var(--sunken)}
.stat b{display:block;font-size:1.32rem;line-height:1.2;font-variant-numeric:tabular-nums}
.stat span{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
h2{font-size:1.05rem;margin:30px 0 12px;padding-bottom:7px;border-bottom:1px solid var(--rule)}
.chart{overflow-x:auto;border:1px solid var(--rule);border-radius:4px;padding:12px;background:var(--paper)}
svg{display:block}
.lbl{font-size:11px;fill:var(--ink)}
.dir{font-size:11px;font-weight:600}
.tw{overflow-x:auto;border:1px solid var(--rule);border-radius:4px}
table{border-collapse:collapse;width:100%;min-width:900px;font-size:13px}
th,td{padding:8px 12px;border-bottom:1px solid var(--rule);text-align:left;vertical-align:top}
th{background:var(--sunken);position:sticky;top:0;font-size:11px;text-transform:uppercase;
letter-spacing:.06em;color:var(--muted)}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.n.up{background:#F0FDF4}td.n.down{background:#FEF2F2}td.n.flat{background:#F9FAFB}
tr.up td.n.up:last-of-type,tr.down td.n.down:last-of-type{font-weight:700}
td.u{color:var(--muted);font-size:12px}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--flat)}
.sep{width:1px;height:15px;background:var(--rule);display:inline-block}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:6px;vertical-align:middle}
.dot.up{background:var(--up)}.dot.down{background:var(--down)}.dot.flat{background:var(--flat)}
.excl{display:block;margin-top:5px;color:var(--muted);font-size:12px}
/* AI Analysis block \u2014 leads the report, above the graph. */
.ai{margin:22px 0 6px;padding:16px 18px;border:1px solid var(--rule);
border-left:3px solid #0B5CAD;border-radius:8px;background:var(--sunken)}
.ai h2{margin:0 0 4px}
.ai ul{margin:10px 0 0;padding-left:20px}
.ai li{margin:0 0 7px;line-height:1.55}
.aisub{margin:0;color:var(--muted);font-size:12.5px}
tr.up td.n.up,tr.down td.n.down{font-weight:600}
.ctx{display:block;font-size:11px;color:var(--muted)}
.rev{color:#EA580C;margin-left:6px;font-weight:700}
footer{margin-top:34px;padding-top:14px;border-top:1px solid var(--rule);color:var(--muted);font-size:12px}
@media print{th{position:static}.chart,.tw{border:none}}
</style></head><body><div class="wrap">
<h1>Variance Analysis${reportName ? ` \u2014 ${escapeHtml(reportName)}` : ""}</h1>
<p class="sub">${escapeHtml(labelA)} &nbsp;vs&nbsp; ${escapeHtml(labelB)}</p>
<div class="cmp">
  <span class="key"><span class="sw" style="background:${COLOR_A}"></span>${escapeHtml(labelA)} \u2014 ${t("comparativeAnalysis.current")}</span>
  <span class="key"><span class="sw" style="background:${COLOR_B}"></span>${escapeHtml(labelB)} \u2014 ${t("comparativeAnalysis.previous")}</span>
  <span class="sep"></span>
  <span class="key up">\u2191 ${t("comparativeAnalysis.legendIncrease")}</span><span class="key flat">\u2192 ${t("comparativeAnalysis.legendNoChange")}</span>
  <span class="key down">\u2193 ${t("comparativeAnalysis.legendDecrease")}</span>
</div>
<div class="cov"><b>${t("export.visualizationAll").replace("{0}", total.toLocaleString())}${meta?.concepts ? ` across ${Number(meta.concepts).toLocaleString()} concepts` : ""}.</b>${meta?.dimensional ? ` ${t("comparativeAnalysis.dimensionalContext").replace("{0}", Number(meta.dimensional).toLocaleString())}` : ""} ${graphIsCritical ? `The graph below shows the <b>${graphRows.length.toLocaleString()}</b> Critical
         regulatory-importance concept(s); the comparison itself covered every fact above.` : "Every comparable fact is drawn below."}${meta?.one_sided ? ` <span class="excl">${Number(meta.one_sided).toLocaleString()} fact(s) reported in only one period are excluded \u2014 they cannot be compared.</span>` : ""}</div>
<div class="stats">
  <div class="stat"><b>${total.toLocaleString()}</b><span>${t("comparativeAnalysis.factsCompared")}</span></div>
  ${meta?.concepts ? `<div class="stat"><b>${Number(meta.concepts).toLocaleString()}</b><span>${t("comparativeAnalysis.concepts")}</span></div>` : ""}
  <div class="stat"><b class="up">${inc.toLocaleString()}</b><span>${t("comparativeAnalysis.increased")}</span></div>
  <div class="stat"><b class="down">${dec.toLocaleString()}</b><span>${t("comparativeAnalysis.decreased")}</span></div>
  <div class="stat"><b class="flat">${flat.toLocaleString()}</b><span>${t("comparativeAnalysis.unchanged")}</span></div>
  ${meta?.sign_changes ? `<div class="stat"><b style="color:#EA580C">${Number(meta.sign_changes).toLocaleString()}</b><span>${t("comparativeAnalysis.reversed")}</span></div>` : ""}
</div>
${analysisHtml}
<h2>${graphIsCritical ? t("comparativeAnalysis.criticalConceptsOf").replace("{0}", graphRows.length.toLocaleString()).replace("{1}", total.toLocaleString()) : t("comparativeAnalysis.currentVsPreviousAll").replace("{0}", total.toLocaleString())}</h2>
${graphIsCritical ? `<p class="aisub">Graph limited to Critical regulatory-importance concepts.
Bars use a signed-log scale so values orders of magnitude apart stay
distinguishable \u2014 hover any bar for the exact figures.</p>` : ""}
<div class="chart"><svg width="${W}" height="${bodyH + 20}" viewBox="0 0 ${W} ${bodyH + 20}"
role="img" aria-label="Paired bars comparing ${escapeHtml(labelA)} against ${escapeHtml(labelB)} for ${graphRows.length} ${graphIsCritical ? "Critical" : "comparable"} facts">
<g transform="translate(0,10)">${bars}</g></svg></div>
<footer>Generated ${escapeHtml(generated)} from iDEAL Xia. Values are exactly as compared \u2014
raw XBRL figures, unmodified. Hover a bar for full precision.</footer>
</div></body></html>`;
}
var ROW_PX = 36;
var ROW_OVERSCAN = 10;
var ROW_WINDOW_MIN = 120;
var TOPN_OPTIONS = [10, 25, 50, "All"];
var DEFAULT_TOPN = 10;
var GROUPED_MAX = 25;
var ROW_PX_LARGE = 58;
var TIER_FILTERS = ["All", "Critical", "High", "Medium", "Low"];
var rankings = (t) => [
  [
    "diff",
    t("comparativeAnalysis.rankAbsoluteDiff"),
    t("comparativeAnalysis.rankAbsoluteDiffDesc")
  ],
  [
    "pct",
    t("comparativeAnalysis.rankPctChange"),
    t("comparativeAnalysis.rankPctChangeDesc")
  ]
];
function VarianceChartModal({ rows, meta, labelA, labelB, summaryText, onClose }) {
  const t = useT();
  const [chartType, setChartType] = useState("bar");
  const [showSig, setShowSig] = useState(false);
  const [useLogScale, setUseLogScale] = useState(true);
  const [filterMode, setFilterMode] = useState("all");
  const [search, setSearch] = useState("");
  const [topN, setTopN] = useState(DEFAULT_TOPN);
  const [rankBy, setRankBy] = useState(null);
  const [tier, setTier] = useState("All");
  const handleKey = useCallback((e) => {
    if (e.key === "Escape") onClose?.();
  }, [onClose]);
  useEffect(() => {
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [handleKey]);
  const { minVal, maxVal, valCount } = useMemo(() => {
    let mn = Infinity, mx = 0, n = 0;
    for (const r of rows) {
      for (const v of [Math.abs(r.val_a ?? 0), Math.abs(r.val_b ?? 0)]) {
        if (v > 0) {
          if (v < mn) mn = v;
          if (v > mx) mx = v;
          n++;
        }
      }
    }
    return { minVal: mn, maxVal: mx, valCount: n };
  }, [rows]);
  const autoLog = valCount > 1 && minVal > 0 && maxVal / minVal > 100;
  const importanceAvailable = Boolean(
    meta?.importance_available ?? rows.some((r) => r.importance_matched)
  );
  const tierCounts = useMemo(() => {
    if (meta?.importance_tiers) return meta.importance_tiers;
    const t2 = {};
    for (const r of rows) {
      if (r.importance_matched && r.importance_tier) {
        t2[r.importance_tier] = (t2[r.importance_tier] ?? 0) + 1;
      }
    }
    return t2;
  }, [rows, meta]);
  const { sigCount, signChgCount, incCount, decCount, flatCount, zeroBaseCount } = useMemo(() => {
    let sig = 0, rev = 0, inc = 0, dec = 0, zero = 0;
    for (const r of rows) {
      if (r.significant) sig++;
      if (r.sign_change) rev++;
      if (r.pct_change === null || r.pct_change === void 0) zero++;
      const d = r.diff ?? 0;
      if (d > 0) inc++;
      else if (d < 0) dec++;
    }
    return {
      sigCount: sig,
      signChgCount: rev,
      incCount: inc,
      decCount: dec,
      flatCount: rows.length - inc - dec,
      zeroBaseCount: zero
    };
  }, [rows]);
  const scrollRef = useRef(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportH, setViewportH] = useState(560);
  const onChartScroll = useCallback((e) => {
    setScrollTop(e.currentTarget.scrollTop);
    setViewportH(e.currentTarget.clientHeight || 560);
  }, []);
  useEffect(() => {
    const el = scrollRef.current;
    if (el) setViewportH(el.clientHeight || 560);
  }, [chartType]);
  const filteredRows = useMemo(() => {
    let out = rows;
    if (filterMode === "sig") out = out.filter((r) => r.significant);
    else if (filterMode === "up") out = out.filter((r) => (r.diff ?? 0) > 0);
    else if (filterMode === "down") out = out.filter((r) => (r.diff ?? 0) < 0);
    else if (filterMode === "reversal") out = out.filter((r) => r.sign_change);
    else if (filterMode === "zero") {
      out = out.filter((r) => r.pct_change === null || r.pct_change === void 0);
    }
    if (tier !== "All") {
      out = out.filter((r) => r.importance_matched && r.importance_tier === tier);
    }
    const q = search.trim().toLowerCase();
    if (q) out = out.filter((r) => (r.concept ?? "").toLowerCase().includes(q));
    return out;
  }, [rows, filterMode, search, tier]);
  const effectiveFiltered = showSig ? filteredRows.filter((r) => r.significant) : filteredRows;
  const rankedRows = useMemo(() => {
    if (!rankBy) return effectiveFiltered;
    const out = [...effectiveFiltered];
    if (rankBy === "diff") {
      out.sort((a, b) => Math.abs(b.diff ?? 0) - Math.abs(a.diff ?? 0));
    } else if (rankBy === "pct") {
      const key = (r) => r.pct_change === null || r.pct_change === void 0 ? -Infinity : Math.abs(r.pct_change);
      out.sort((a, b) => key(b) - key(a));
    }
    return out;
  }, [effectiveFiltered, rankBy]);
  const cappedRows = useMemo(
    () => topN === "All" ? rankedRows : rankedRows.slice(0, topN),
    [rankedRows, topN]
  );
  const hiddenByCap = rankedRows.length - cappedRows.length;
  const grouped = cappedRows.length > 0 && cappedRows.length <= GROUPED_MAX;
  const rowPx = grouped ? ROW_PX_LARGE : ROW_PX;
  const visibleRows = cappedRows;
  const totalRows = visibleRows.length;
  const windowed = totalRows > ROW_WINDOW_MIN;
  const startIdx = windowed ? Math.max(0, Math.floor(scrollTop / rowPx) - ROW_OVERSCAN) : 0;
  const endIdx = windowed ? Math.min(totalRows, Math.ceil((scrollTop + viewportH) / rowPx) + ROW_OVERSCAN) : totalRows;
  const windowRows = windowed ? visibleRows.slice(startIdx, endIdx) : visibleRows;
  const spacerH = totalRows * rowPx;
  const offsetY = startIdx * rowPx;
  const handleDownloadHtml = useCallback(() => {
    const html = buildStandaloneHtml({ rows, meta, labelA, labelB, reportName: "", summaryText, lang: t.lang });
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const safe = (s) => String(s || "").replace(/[^A-Za-z0-9._-]+/g, "-").slice(0, 40);
    a.href = url;
    a.download = `variance-${safe(labelA)}-vs-${safe(labelB)}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }, [rows, meta, labelA, labelB, summaryText]);
  const FILTER_META = {
    up: { arrow: "\u2191 ", color: COLOR_POS },
    down: { arrow: "\u2193 ", color: COLOR_NEG },
    reversal: { arrow: "\u21D5 ", color: COLOR_SIGN }
  };
  const FILTERS = [
    [
      "all",
      `${t("common.all")} (${rows.length.toLocaleString()})`,
      t("comparativeAnalysis.filters.allDesc")
    ],
    [
      "sig",
      `${t("comparativeAnalysis.highVariance")} (${sigCount.toLocaleString()})`,
      t("comparativeAnalysis.filters.sigDesc")
    ],
    [
      "up",
      `${t("comparativeAnalysis.increased")} (${incCount.toLocaleString()})`,
      t("comparativeAnalysis.filters.upDesc")
    ],
    [
      "down",
      `${t("comparativeAnalysis.decreased")} (${decCount.toLocaleString()})`,
      t("comparativeAnalysis.filters.downDesc")
    ],
    [
      "reversal",
      `${t("comparativeAnalysis.reversed")} (${signChgCount.toLocaleString()})`,
      t("comparativeAnalysis.filters.reversalDesc")
    ],
    // "Previous was 0" rather than "From zero": the first reading of the label
    // should already be the explanation. Users asked what "From zero" meant.
    [
      "zero",
      t("comparativeAnalysis.previousWas0Count").replace("{0}", zeroBaseCount.toLocaleString()),
      t("comparativeAnalysis.zeroBaselineNote")
    ]
  ];
  const sourceRows = windowRows;
  const chartData = sourceRows.map((r) => ({
    name: shortLabel(r.concept),
    fullName: r.concept,
    // Raw values for accurate chart rendering
    [labelA]: r.val_a ?? 0,
    [labelB]: r.val_b ?? 0,
    // Signed-log-transformed values for the log-scale variant
    [`${labelA}_log`]: signedLog(r.val_a ?? 0),
    [`${labelB}_log`]: signedLog(r.val_b ?? 0),
    // % change for the pct view
    pct_display: r.pct_change ?? 0,
    pct_change: r.pct_change,
    significant: r.significant,
    sign_change: r.sign_change,
    unit: r.unit,
    anomaly_flags: r.anomaly_flags,
    severity: r.severity
  }));
  const effectiveLog = useLogScale || autoLog;
  const barFillA = () => COLOR_A;
  const barFillB = () => COLOR_B;
  const barStroke = (entry) => entry.sign_change ? COLOR_SIGN : "none";
  const pctFill = (entry) => {
    const v = entry.pct_display ?? 0;
    if (v > 0) return COLOR_POS;
    if (v < 0) return COLOR_NEG;
    return COLOR_FLAT;
  };
  const dominantFill = (fillOf, fallback) => {
    const tally = /* @__PURE__ */ new Map();
    for (const entry of chartData) {
      const colour = fillOf(entry);
      tally.set(colour, (tally.get(colour) ?? 0) + 1);
    }
    let best = fallback;
    let bestCount = 0;
    for (const [colour, count] of tally) {
      if (count > bestCount) {
        best = colour;
        bestCount = count;
      }
    }
    return best;
  };
  const legendFillA = COLOR_A;
  const legendFillB = COLOR_B;
  const legendFillPct = dominantFill(pctFill, COLOR_POS);
  const aKey = effectiveLog && chartType !== "pct" ? `${labelA}_log` : labelA;
  const bKey = effectiveLog && chartType !== "pct" ? `${labelB}_log` : labelB;
  const pctTickFmt = (v) => {
    const abs = Math.abs(v);
    if (abs > 1e4) return `${v > 0 ? "+" : ""}Ext`;
    if (abs > 1e3) return `${v > 0 ? "+" : ""}${(v / 1e3).toFixed(1)}K%`;
    return `${v >= 0 ? "+" : ""}${v.toFixed(0)}%`;
  };
  const sharedChartProps = {
    data: chartData,
    layout: "vertical",
    margin: { top: 10, right: 30, bottom: 10, left: 10 }
  };
  const sharedXAxis = /* @__PURE__ */ h(
    XAxis,
    {
      type: "number",
      tickFormatter: effectiveLog ? fmtLogAxis : fmtAxis,
      tick: { fontSize: 11, fill: "#6B7280" },
      width: 70
    }
  );
  const sharedYAxis = /* @__PURE__ */ h(
    YAxis,
    {
      type: "category",
      dataKey: "fullName",
      tick: { fontSize: 11, fill: "#6B7280", textAnchor: "end" },
      width: 250,
      tickLine: false,
      dx: -4
    }
  );
  const sharedGrid = /* @__PURE__ */ h(CartesianGrid, { strokeDasharray: "3 3", stroke: "rgba(100,120,160,0.15)" });
  const sharedLegend = /* @__PURE__ */ h(
    Legend,
    {
      verticalAlign: "top",
      align: "center",
      wrapperStyle: { fontSize: 12, paddingBottom: 10 }
    }
  );
  const sharedTooltip = /* @__PURE__ */ h(
    Tooltip,
    {
      content: /* @__PURE__ */ h(VarTooltip, { labelA, labelB }),
      cursor: { fill: "rgba(11,92,173,0.07)" }
    }
  );
  const chartHeight = Math.max(340, chartData.length * rowPx + 60);
  return (
    /* backdrop */
    /* @__PURE__ */ h("div", { className: "vc-backdrop", onClick: (e) => {
      if (e.target === e.currentTarget) onClose?.();
    } }, /* @__PURE__ */ h("div", { className: "vc-modal", role: "dialog", "aria-modal": "true", "aria-label": t("comparativeAnalysis.chartTitle") }, /* @__PURE__ */ h("div", { className: "vc-header" }, /* @__PURE__ */ h("div", { className: "vc-title" }, /* @__PURE__ */ h("span", { className: "vc-title-icon" }, "\u{1F4CA}"), t("comparativeAnalysis.title"), /* @__PURE__ */ h("span", { className: "vc-title-labels" }, /* @__PURE__ */ h("span", { className: "vc-label-a" }, labelA), /* @__PURE__ */ h("span", { className: "vc-vs" }, "vs"), /* @__PURE__ */ h("span", { className: "vc-label-b" }, labelB))), /* @__PURE__ */ h("div", { className: "vc-header-controls" }, /* @__PURE__ */ h(
      "button",
      {
        className: "vc-download-btn-main",
        onClick: handleDownloadHtml,
        title: t("comparativeAnalysis.downloadTooltip").replace("{0}", rows.length.toLocaleString())
      },
      "\u2B73 ",
      t("common.download")
    ), /* @__PURE__ */ h("div", { className: "vc-toggle-group" }, /* @__PURE__ */ h(
      "button",
      {
        className: `vc-toggle-btn${chartType === "bar" ? " active" : ""}`,
        onClick: () => setChartType("bar")
      },
      "\u25A6 ",
      t("comparativeAnalysis.chartBar")
    ), /* @__PURE__ */ h(
      "button",
      {
        className: `vc-toggle-btn${chartType === "line" ? " active" : ""}`,
        onClick: () => setChartType("line")
      },
      "\u3030 ",
      t("comparativeAnalysis.chartLine")
    ), /* @__PURE__ */ h(
      "button",
      {
        className: `vc-toggle-btn${chartType === "pct" ? " active" : ""}`,
        onClick: () => setChartType("pct"),
        title: t("comparativeAnalysis.showPctChange")
      },
      "% Chg"
    )), /* @__PURE__ */ h("button", { className: "vc-close-btn", onClick: onClose, "aria-label": t("comparativeAnalysis.closeChart") }, "\u2715"))), /* @__PURE__ */ h("div", { className: "vc-summary" }, /* @__PURE__ */ h(
      "div",
      {
        className: "vc-sum-card",
        title: [
          t("comparativeAnalysis.factsBoth").replace("{0}", rows.length.toLocaleString()).replace("{1}", labelA).replace("{2}", labelB),
          meta?.one_sided ? t("comparativeAnalysis.oneSidedExcluded").replace("{0}", Number(meta.one_sided).toLocaleString()) : "",
          meta?.dimensional ? t("comparativeAnalysis.dimensionalContext").replace("{0}", Number(meta.dimensional).toLocaleString()) : ""
        ].filter(Boolean).join("\n")
      },
      /* @__PURE__ */ h("span", { className: "vc-sum-label" }, t("comparativeAnalysis.comparableFacts")),
      /* @__PURE__ */ h("span", { className: "vc-sum-val" }, rows.length.toLocaleString())
    ), meta?.concepts ? /* @__PURE__ */ h("div", { className: "vc-sum-card" }, /* @__PURE__ */ h("span", { className: "vc-sum-label" }, t("comparativeAnalysis.concepts")), /* @__PURE__ */ h("span", { className: "vc-sum-val" }, Number(meta.concepts).toLocaleString())) : null, /* @__PURE__ */ h("div", { className: "vc-sum-card" }, /* @__PURE__ */ h("span", { className: "vc-sum-label" }, t("comparativeAnalysis.increased")), /* @__PURE__ */ h("span", { className: "vc-sum-val", style: { color: COLOR_POS } }, incCount.toLocaleString())), /* @__PURE__ */ h("div", { className: "vc-sum-card" }, /* @__PURE__ */ h("span", { className: "vc-sum-label" }, t("comparativeAnalysis.decreased")), /* @__PURE__ */ h("span", { className: "vc-sum-val", style: { color: COLOR_NEG } }, decCount.toLocaleString())), /* @__PURE__ */ h("div", { className: "vc-sum-card" }, /* @__PURE__ */ h("span", { className: "vc-sum-label" }, t("comparativeAnalysis.noChange")), /* @__PURE__ */ h("span", { className: "vc-sum-val", style: { color: COLOR_FLAT } }, flatCount.toLocaleString())), signChgCount > 0 ? /* @__PURE__ */ h("div", { className: "vc-sum-card" }, /* @__PURE__ */ h("span", { className: "vc-sum-label" }, t("comparativeAnalysis.reversed")), /* @__PURE__ */ h("span", { className: "vc-sum-val", style: { color: COLOR_SIGN } }, signChgCount.toLocaleString())) : null, /* @__PURE__ */ h("div", { className: "vc-period-badge" }, /* @__PURE__ */ h("span", { className: "vc-pl-item" }, /* @__PURE__ */ h("span", { className: "vc-pl-swatch", style: { background: COLOR_A } }), labelA, " ", /* @__PURE__ */ h("em", null, t("comparativeAnalysis.current"))), /* @__PURE__ */ h("span", { className: "vc-pl-item" }, /* @__PURE__ */ h("span", { className: "vc-pl-swatch", style: { background: COLOR_B } }), labelB, " ", /* @__PURE__ */ h("em", null, t("comparativeAnalysis.previous"))))), /* @__PURE__ */ h("div", { className: "vc-filterbar" }, /* @__PURE__ */ h("div", { className: "vc-fb-row" }, /* @__PURE__ */ h("div", { className: "vc-controls" }, /* @__PURE__ */ h("div", { className: "vc-filter-group" }, FILTERS.map(([key, label, hint]) => {
      const meta2 = FILTER_META[key];
      const active = filterMode === key;
      return /* @__PURE__ */ h(
        "button",
        {
          key,
          className: `vc-chip${active ? " active" : ""}`,
          onClick: () => setFilterMode(key),
          title: hint,
          style: meta2 ? active ? { background: meta2.color, borderColor: meta2.color, color: "#fff" } : { color: meta2.color, borderColor: meta2.color } : void 0
        },
        meta2 ? meta2.arrow : "",
        label
      );
    }))), /* @__PURE__ */ h("div", { className: "vc-search-col" }, /* @__PURE__ */ h(
      "input",
      {
        className: "vc-search",
        type: "search",
        placeholder: t("comparativeAnalysis.searchConceptName"),
        value: search,
        onChange: (e) => setSearch(e.target.value),
        "aria-label": t("comparativeAnalysis.filterChartTooltip"),
        title: t("comparativeAnalysis.filterNoteChart")
      }
    )), /* @__PURE__ */ h("div", { className: "vc-controls vc-controls-rank" }, /* @__PURE__ */ h("div", { className: "vc-rank-group" }, /* @__PURE__ */ h("label", { className: "vc-rank-label", htmlFor: "vc-topn" }, t("common.show")), /* @__PURE__ */ h(
      "select",
      {
        id: "vc-topn",
        className: "vc-select",
        value: String(topN),
        onChange: (e) => {
          const v = e.target.value;
          setTopN(v === "All" ? "All" : Number(v));
        },
        title: t("comparativeAnalysis.rowsNoteChart")
      },
      TOPN_OPTIONS.map((opt) => /* @__PURE__ */ h("option", { key: String(opt), value: String(opt) }, opt === "All" ? t("common.all") : t("comparativeAnalysis.topN").replace("{0}", String(opt))))
    )), importanceAvailable && /* @__PURE__ */ h("div", { className: "vc-rank-group" }, /* @__PURE__ */ h("label", { className: "vc-rank-label", htmlFor: "vc-tier" }, t("comparativeAnalysis.importance")), /* @__PURE__ */ h(
      "select",
      {
        id: "vc-tier",
        className: "vc-select",
        value: tier,
        onChange: (e) => setTier(e.target.value),
        title: t("comparativeAnalysis.tierFilterTooltip")
      },
      TIER_FILTERS.map((t2) => {
        const n = t2 === "All" ? rows.length : tierCounts[t2] ?? 0;
        return /* @__PURE__ */ h("option", { key: t2, value: t2 }, t2, n ? ` (${n.toLocaleString()})` : "");
      })
    )), /* @__PURE__ */ h("div", { className: "vc-rank-group" }, /* @__PURE__ */ h("span", { className: "vc-rank-label" }, t("comparativeAnalysis.rankedBy")), rankings(t).map(([key, label, hint]) => {
      const active = rankBy === key;
      return /* @__PURE__ */ h(
        "button",
        {
          key,
          type: "button",
          className: `vc-chip vc-chip-sm${active ? " active" : ""}`,
          onClick: () => setRankBy(active ? null : key),
          "aria-pressed": active,
          title: active ? `${hint}

Click again to restore the default order.` : hint
        },
        label
      );
    }))))), /* @__PURE__ */ h("div", { className: "vc-coverage" }, hiddenByCap > 0 ? /* @__PURE__ */ h(F, null, t("comparativeAnalysis.showingTopOf").replace("{0}", cappedRows.length.toLocaleString()).replace("{1}", rankedRows.length.toLocaleString()), " ", filterMode === "all" && !search.trim() && tier === "All" ? t("comparativeAnalysis.comparableFacts") : t("comparativeAnalysis.matchingFacts"), " \xB7 ", t("comparativeAnalysis.rankedBySep"), " ", /* @__PURE__ */ h("b", null, (rankings(t).find(([k]) => k === rankBy) || [, t("comparativeAnalysis.defaultRanking")])[1]), tier !== "All" ? /* @__PURE__ */ h(F, null, " \xB7 ", t("comparativeAnalysis.tierSep"), " ", /* @__PURE__ */ h("b", null, tier)) : null) : /* @__PURE__ */ h(F, null, t("comparativeAnalysis.showingAll").replace("{0}", cappedRows.length.toLocaleString()), " ", filterMode === "all" && !search.trim() && tier === "All" ? t("comparativeAnalysis.comparableFacts") : t("comparativeAnalysis.matchingFacts"), tier !== "All" ? /* @__PURE__ */ h(F, null, " ", t("comparativeAnalysis.inTier"), " ", /* @__PURE__ */ h("b", null, tier)) : null), " \xB7 ", /* @__PURE__ */ h("span", { className: "vc-cov-up" }, t("comparativeAnalysis.countUp").replace("{0}", incCount.toLocaleString())), " \xB7 ", /* @__PURE__ */ h("span", { className: "vc-cov-down" }, t("comparativeAnalysis.countDown").replace("{0}", decCount.toLocaleString())), flatCount > 0 ? /* @__PURE__ */ h(F, null, " \xB7 ", t("comparativeAnalysis.countUnchanged").replace("{0}", flatCount.toLocaleString())) : null, hiddenByCap > 0 || filterMode !== "all" || search.trim() ? /* @__PURE__ */ h("span", { className: "vc-cov-note" }, " ", t("comparativeAnalysis.directionCountsNote").replace("{0}", rows.length.toLocaleString())) : null, " \xB7 ", /* @__PURE__ */ h("span", { className: "vc-cov-note" }, t("comparativeAnalysis.downloadNote"))), /* @__PURE__ */ h("div", { className: "vc-chart-wrap" }, /* @__PURE__ */ h(
      "div",
      {
        className: "vc-chart-area",
        ref: scrollRef,
        onScroll: onChartScroll,
        style: { overflowY: "auto", maxHeight: "65vh", scrollbarGutter: "stable" }
      },
      /* @__PURE__ */ h("div", { style: windowed ? { height: spacerH, position: "relative" } : void 0 }, /* @__PURE__ */ h("div", { style: windowed ? { position: "absolute", top: offsetY, left: 0, right: 0 } : void 0 }, chartData.length === 0 ? /* @__PURE__ */ h("div", { className: "vc-empty" }, t("comparativeAnalysis.noRows")) : chartType === "pct" ? (
        /* ── % Change chart ── */
        /* @__PURE__ */ h(ResponsiveContainer, { width: "100%", height: chartHeight }, /* @__PURE__ */ h(
          BarChart,
          {
            data: chartData,
            layout: "vertical",
            margin: { top: 10, right: 30, bottom: 10, left: 10 }
          },
          sharedGrid,
          /* @__PURE__ */ h(
            XAxis,
            {
              type: "number",
              tickFormatter: pctTickFmt,
              tick: { fontSize: 11, fill: "#6B7280" },
              width: 70
            }
          ),
          /* @__PURE__ */ h(
            YAxis,
            {
              type: "category",
              dataKey: "name",
              tick: { fontSize: 11, fill: "#6B7280" },
              width: 220,
              tickLine: false
            }
          ),
          sharedTooltip,
          /* @__PURE__ */ h(Legend, { wrapperStyle: { fontSize: 12, paddingBottom: 10 }, verticalAlign: "top" }),
          /* @__PURE__ */ h(ReferenceLine, { x: 0, stroke: "rgba(100,120,160,0.3)" }),
          "   ",
          /* @__PURE__ */ h(Bar, { dataKey: "pct_display", name: "% Change", fill: legendFillPct, radius: [0, 4, 4, 0], maxBarSize: 22, animationDuration: 600 }, chartData.map((entry, i) => /* @__PURE__ */ h(Cell, { key: i, fill: pctFill(entry) })), grouped && /* @__PURE__ */ h(
            LabelList,
            {
              dataKey: "pct_display",
              position: "right",
              formatter: pctTickFmt,
              style: { fontSize: 10, fill: "#475569" }
            }
          ))
        ))
      ) : /* @__PURE__ */ h(ResponsiveContainer, { width: "100%", height: chartHeight }, chartType === "bar" ? /* @__PURE__ */ h(BarChart, { ...sharedChartProps }, sharedGrid, sharedXAxis, sharedYAxis, sharedTooltip, /* @__PURE__ */ h(ReferenceLine, { x: 0, stroke: "rgba(100,120,160,0.3)" }), "   ", /* @__PURE__ */ h(Bar, { dataKey: aKey, name: `${labelA} \u2014 Current`, fill: legendFillA, radius: [0, 4, 4, 0], maxBarSize: grouped ? 18 : 22, minPointSize: 3, animationDuration: 600 }, chartData.map((entry, i) => /* @__PURE__ */ h(Cell, { key: i, fill: barFillA(entry), stroke: barStroke(entry), strokeWidth: entry.sign_change ? 1.5 : 0 })), grouped && /* @__PURE__ */ h(
        LabelList,
        {
          dataKey: labelA,
          position: "right",
          formatter: fmtAxis,
          style: { fontSize: 10, fill: "#475569" }
        }
      )), /* @__PURE__ */ h(Bar, { dataKey: bKey, name: `${labelB} \u2014 Previous`, fill: legendFillB, radius: [0, 4, 4, 0], maxBarSize: grouped ? 18 : 22, minPointSize: 3, animationDuration: 600 }, chartData.map((entry, i) => /* @__PURE__ */ h(Cell, { key: i, fill: barFillB(entry), stroke: barStroke(entry), strokeWidth: entry.sign_change ? 1.5 : 0 })), grouped && /* @__PURE__ */ h(
        LabelList,
        {
          dataKey: labelB,
          position: "right",
          formatter: fmtAxis,
          style: { fontSize: 10, fill: "#475569" }
        }
      ))) : /* @__PURE__ */ h(LineChart, { ...sharedChartProps }, sharedGrid, sharedXAxis, sharedYAxis, sharedTooltip, /* @__PURE__ */ h(ReferenceLine, { x: 0, stroke: "rgba(100,120,160,0.3)" }), "   ", /* @__PURE__ */ h(
        Line,
        {
          type: "monotone",
          dataKey: aKey,
          name: `${labelA} \u2014 Current`,
          stroke: COLOR_A,
          strokeWidth: 2.5,
          dot: { r: 4, fill: COLOR_A, strokeWidth: 0 },
          activeDot: { r: 6 },
          animationDuration: 600
        }
      ), /* @__PURE__ */ h(
        Line,
        {
          type: "monotone",
          dataKey: bKey,
          name: `${labelB} \u2014 Previous`,
          stroke: COLOR_B,
          strokeWidth: 2.5,
          dot: { r: 4, fill: COLOR_B, strokeWidth: 0 },
          activeDot: { r: 6 },
          animationDuration: 600
        }
      )))))
    ))))
  );
}

// src/services/api.js
var BASE_URL = "";
function _err(detail, i18nKey) {
  const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((d) => d?.msg || "").filter(Boolean).join("; ") : "";
  const e = new Error(msg);
  e.i18nKey = i18nKey;
  return e;
}
async function _postJson(path, body, signal, i18nKey) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw _err(err.detail, i18nKey);
  }
  return res.json();
}
async function getAllowedActions(loginId, opts = {}) {
  const { tenantId, domain } = opts;
  const params = new URLSearchParams();
  if (loginId) params.set("login_id", loginId);
  if (tenantId) params.set("tenant_id", tenantId);
  if (domain) params.set("domain", domain);
  const qs = params.toString();
  const res = await fetch(`${BASE_URL}/allowed-actions${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw _err("", "errors.fetchActions");
  const data = await res.json();
  return Array.isArray(data?.actions) ? data.actions : [];
}
async function stopRequest(requestId) {
  if (!requestId) return;
  try {
    await fetch(`${BASE_URL}/stop`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_id: requestId })
    });
  } catch {
  }
}
async function sendFeedback(rating, context = {}) {
  const { query = null, intent = null, resultType = null, sessionId = null } = context;
  try {
    await fetch(`${BASE_URL}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rating,
        query,
        intent,
        result_type: resultType,
        session_id: sessionId
      })
    });
  } catch {
  }
}
async function compareInstances(sessionId, instanceA, instanceB, opts = {}) {
  const { signal, requestId, lang, tenantId, domain, jwt } = opts;
  const body = {
    session_id: sessionId,
    instance_a: instanceA,
    instance_b: instanceB,
    request_id: requestId ?? null
  };
  if (lang && lang !== "en") body.lang = lang;
  if (tenantId) body.tenant_id = tenantId;
  if (domain) body.domain = domain;
  if (jwt) body.jwt = jwt;
  return _postJson("/compare-execute", body, signal, "errors.compareFailed");
}
async function fetchCompareSummary(rows, labelA, labelB, reportName, opts = {}) {
  const { signal, requestId, lang, loginId, tenantId, domain, jwt } = opts;
  try {
    const res = await fetch(`${BASE_URL}/compare-summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rows: (rows ?? []).map((r) => ({
          concept: r.concept ?? "",
          val_a: r.val_a ?? null,
          val_b: r.val_b ?? null,
          diff: r.diff ?? null,
          pct_change: r.pct_change ?? null,
          significant: Boolean(r.significant),
          // Regulatory-importance context, echoed back so the async narrative
          // names the same supervisory section the table on screen was ranked
          // by. Empty for a return whose taxonomy could not be read, and the
          // backend prompt then falls back to plain variance wording.
          section: r.section ?? "",
          importance_tier: r.importance_tier ?? "",
          mandated_by: Array.isArray(r.mandated_by) ? r.mandated_by.slice(0, 8) : [],
          // Needed to SELECT and describe the facts server-side: concept_base
          // drives the max-3-variants-per-concept cap, context_key locates the
          // parent row for share-of-total, unit decides whether ₹ Cr applies,
          // and priority is the 60/40 order the selection slices.
          concept_base: r.concept_base ?? r.concept ?? "",
          context_key: r.context_key ?? "BASE",
          unit: r.unit ?? "",
          section_code: r.section_code ?? "",
          importance: r.importance ?? null,
          priority: r.priority ?? null,
          importance_matched: Boolean(r.importance_matched),
          // The names the table shows, so the AI narrative uses them too instead
          // of the technical codes.
          concept_label: r.concept_label ?? "",
          member_labels: Array.isArray(r.member_labels) ? r.member_labels.slice(0, 16).map((m) => m ?? "") : []
        })),
        label_a: labelA ?? "",
        label_b: labelB ?? "",
        report_name: reportName ?? "",
        request_id: requestId ?? null,
        // M-05: /compare-summary now requires a resolvable login_id when the
        // backend's REQUIRE_AUTH is on -- without this the endpoint 403s and
        // this function's own catch-all silently resolves to '', which is
        // exactly what showed up as "AI analysis is unavailable" with no
        // visible error.
        login_id: loginId ?? null,
        // APP_VERSION=6.0: without these, login_id above is checked against
        // the default/unscoped repo root instead of the caller's own
        // tenant, is never resolved, and the endpoint 403s every time --
        // the same CHATBOT_AUTH-sourced values every other 6.0-aware call
        // (sendMessage/compareInstances/explainErrorCategory) already sends.
        // All null/no-op for 5.5.
        tenant_id: tenantId ?? null,
        domain: domain ?? null,
        jwt: jwt ?? null,
        // The AI narrative is model-authored, so it is translated at runtime by
        // the existing boundary. Omitted / 'en' leaves it in English.
        ...lang && lang !== "en" ? { lang } : {}
      }),
      signal
    });
    if (!res.ok) return "";
    const data = await res.json().catch(() => ({}));
    return data.llm_summary ?? "";
  } catch {
    return "";
  }
}
async function sendMessage(message, sessionId = null, aspSession = null, loginId = null, userId = null, roleId = null, conversationHistory = [], opts = {}) {
  const { signal, requestId, tenantId, domain, jwt, lang } = opts;
  const body = { message };
  if (lang && lang !== "en") body.lang = lang;
  if (sessionId) body.session_id = sessionId;
  if (aspSession) body.asp_session = aspSession;
  if (loginId) body.login_id = loginId;
  if (userId) body.user_id = userId;
  if (roleId) body.role_id = roleId;
  if (conversationHistory?.length) body.conversation_history = conversationHistory;
  if (requestId) body.request_id = requestId;
  if (tenantId) body.tenant_id = tenantId;
  if (domain) body.domain = domain;
  if (jwt) body.jwt = jwt;
  return _postJson("/chat", body, signal, "errors.requestFailed");
}
async function sendGuidedMessage(message, sessionId = null, aspSession = null, loginId = null, userId = null, roleId = null, opts = {}) {
  const { signal, requestId, tenantId, domain, jwt, lang } = opts;
  const body = { message };
  if (lang && lang !== "en") body.lang = lang;
  if (sessionId) body.session_id = sessionId;
  if (aspSession) body.asp_session = aspSession;
  if (loginId) body.login_id = loginId;
  if (userId) body.user_id = userId;
  if (roleId) body.role_id = roleId;
  if (requestId) body.request_id = requestId;
  if (tenantId) body.tenant_id = tenantId;
  if (domain) body.domain = domain;
  if (jwt) body.jwt = jwt;
  return _postJson("/guided", body, signal, "errors.requestFailed");
}
async function transcribeAudio(audioBlob, opts = {}) {
  const { signal, lang, requestId } = opts;
  const formData = new FormData();
  const ext = audioBlob.type.includes("webm") ? "webm" : audioBlob.type.includes("ogg") ? "ogg" : audioBlob.type.includes("mp4") ? "mp4" : "audio";
  formData.append("file", audioBlob, `recording.${ext}`);
  if (lang) formData.append("lang", lang);
  if (requestId) formData.append("request_id", requestId);
  const res = await fetch(`${BASE_URL}/speech-to-text`, {
    method: "POST",
    body: formData,
    // Do NOT set Content-Type manually — browser sets it with the boundary
    signal
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw _err(body.detail, "voice.transcribeFailed");
  }
  const data = await res.json();
  return data.transcript ?? "";
}
async function explainErrorCategory(errorFilePath, category, formId = null, reportName = null, opts = {}) {
  const { signal, requestId, offset, lang, tenantId, domain, jwt } = opts;
  const body = { filename: errorFilePath, category, form_id: formId };
  if (lang && lang !== "en") body.lang = lang;
  if (reportName) body.report_name = reportName;
  if (requestId) body.request_id = requestId;
  if (offset) body.offset = offset;
  if (tenantId) body.tenant_id = tenantId;
  if (domain) body.domain = domain;
  if (jwt) body.jwt = jwt;
  return _postJson("/explain-category", body, signal, "errors.explanationFailed");
}
async function fetchStatusErrors(jobId, opts = {}) {
  const { lang, loginId, signal } = opts;
  const params = new URLSearchParams();
  if (lang && lang !== "en") params.set("lang", lang);
  if (loginId) params.set("login_id", loginId);
  const qs = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${BASE_URL}/status-errors/${jobId}${qs}`, { signal });
  if (!res.ok) throw _err("", "errors.requestFailed");
  return res.json();
}

// src/components/MessageBubble.jsx
function triggerBlobDownload(url, label) {
  const filename = (() => {
    try {
      return new URL(url, window.location.origin).searchParams.get("filename") || label;
    } catch {
      return label;
    }
  })();
  fetch(url).then((res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.blob();
  }).then((blob) => {
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(blobUrl);
  }).catch(() => {
  });
}
var FAILED_STATUS_CODES = /* @__PURE__ */ new Set([3, 5, 8, 10, 13]);
function detectErrorCategory(details) {
  if (!Array.isArray(details) || details.length === 0) return "none";
  const first = details[0];
  const tag = first?._error_category ?? "";
  if (tag) return tag;
  if (first?.rule_name !== void 0 && first?.formula_type !== void 0) return "formula_error";
  if (first?.error_class !== void 0 && first?.concept !== void 0) return "dimensional";
  if (first?.table_info !== void 0) return "xbrl_schema_other";
  return "unknown";
}
var _CAT_META = {
  formula_error: { icon: "\u2699", label: "Formula Error", color: "#9b59b6" },
  quality_check_error: { icon: "\u{1F50D}", label: "Quality Check", color: "#e67e22" },
  specification_error: { icon: "\u{1F4CB}", label: "Specification Error", color: "#c0392b" },
  xbrl_schema_other: { icon: "\u26A0", label: "Schema Error", color: "#c0392b" },
  dimensional: { icon: "\u{1F4D0}", label: "Dimensional Error", color: "#2980b9" },
  unknown: { icon: "\u26A0", label: "Validation Error", color: "#c0392b" }
};
function _catMeta(tag) {
  return _CAT_META[tag] ?? _CAT_META["unknown"];
}
var _ERROR_PANEL_STYLES = `
/* \u2500\u2500 Error panel wrapper \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 */

`;
if (typeof document !== "undefined" && !document.getElementById("error-panel-styles")) {
  const s = document.createElement("style");
  s.id = "error-panel-styles";
  s.textContent = _ERROR_PANEL_STYLES;
  document.head.appendChild(s);
}
function DownloadButton({ downloadUrl, downloadLabel, className = "download-btn" }) {
  const t = useT();
  const API_BASE = "";
  if (!downloadUrl) return null;
  return /* @__PURE__ */ h(
    "button",
    {
      className,
      onClick: () => triggerBlobDownload(`${API_BASE}${downloadUrl}`, downloadLabel)
    },
    "\u2B07 ",
    downloadLabel || "Download"
  );
}
var summaryCatMeta = (t) => ({
  formula_error: { label: t("errors.category.formulaErrors"), btnLabel: t("errors.explainFormula"), cls: "formula", icon: "\u2699" },
  xbrl_schema: { label: t("errors.category.schemaErrors"), btnLabel: t("errors.explainSchema"), cls: "xbrl", icon: "\u26A0" },
  dimensional: { label: t("errors.category.dimensionErrors"), btnLabel: t("errors.explainDimension"), cls: "dimension", icon: "\u{1F4D0}" }
});
var _CAT_ORDER = ["formula_error", "xbrl_schema", "dimensional"];
function ErrorSummaryPanel({ counts, downloadUrl, downloadLabel, onExplainCategory, formId, reportName, explainableCategories = _CAT_ORDER }) {
  const t = useT();
  const API_BASE = "";
  const [loadingCat, setLoadingCat] = useState2(null);
  const errorFilePath = counts?.filename ?? "";
  const activeCategories = _CAT_ORDER.filter(
    (cat) => counts && counts[cat] && counts[cat] > 0
  );
  const explainableActiveCategories = activeCategories.filter(
    (cat) => explainableCategories.includes(cat)
  );
  const handleExplain = async (cat) => {
    if (loadingCat) return;
    setLoadingCat(cat);
    try {
      await onExplainCategory?.(cat, errorFilePath, formId, reportName);
    } finally {
      setLoadingCat(null);
    }
  };
  return /* @__PURE__ */ h("div", { className: "error-summary-panel" }, /* @__PURE__ */ h("div", { className: "error-summary-heading" }, "\u26A0 ", t("errors.summaryHeading")), /* @__PURE__ */ h("div", { className: "error-summary-body" }, activeCategories.length > 0 && /* @__PURE__ */ h("div", { className: "error-summary-counts" }, activeCategories.map((cat) => {
    const meta = summaryCatMeta(t)[cat];
    return /* @__PURE__ */ h("div", { key: cat, className: `error-count-chip ${meta.cls}` }, /* @__PURE__ */ h("span", null, meta.icon), /* @__PURE__ */ h("span", null, meta.label, ":"), /* @__PURE__ */ h("span", { className: "error-count-num" }, counts[cat]));
  })), /* @__PURE__ */ h("div", { className: "error-summary-actions" }, explainableActiveCategories.map((cat) => {
    const meta = summaryCatMeta(t)[cat];
    const isLoading = loadingCat === cat;
    return /* @__PURE__ */ h(
      "button",
      {
        key: cat,
        className: `explain-cat-btn ${meta.cls}`,
        onClick: () => handleExplain(cat),
        disabled: !!loadingCat
      },
      isLoading ? /* @__PURE__ */ h(F, null, /* @__PURE__ */ h("span", { className: "btn-spinner" }), " ", t("common.generating")) : /* @__PURE__ */ h(F, null, meta.icon, " ", meta.btnLabel)
    );
  }), downloadUrl && /* @__PURE__ */ h(
    "button",
    {
      className: "error-summary-dl-btn",
      onClick: () => triggerBlobDownload(`${API_BASE}${downloadUrl}`, downloadLabel)
    },
    "\u2B07 ",
    downloadLabel || t("errors.downloadReport")
  ))));
}
function ExplainNextErrorsButton({ category, errorFilePath, formId, reportName, nextOffset, onExplainCategory }) {
  const t = useT();
  const [loading, setLoading] = useState2(false);
  const meta = summaryCatMeta(t)[category] || { icon: "\u2699", label: category };
  const handleClick = async () => {
    if (loading) return;
    setLoading(true);
    try {
      await onExplainCategory?.(category, errorFilePath, formId, reportName, nextOffset);
    } finally {
      setLoading(false);
    }
  };
  return /* @__PURE__ */ h("div", { className: "explain-next-errors-wrap" }, /* @__PURE__ */ h(
    "button",
    {
      className: `explain-cat-btn ${meta.cls || ""}`,
      onClick: handleClick,
      disabled: loading
    },
    loading ? /* @__PURE__ */ h(F, null, /* @__PURE__ */ h("span", { className: "btn-spinner" }), " ", t("common.generating")) : /* @__PURE__ */ h(F, null, meta.icon, " ", t("errors.explainNext"))
  ));
}
function _parseFormulaBulletItem(line) {
  const body = line.replace(/^- /, "");
  const boldMatch = body.match(/^\*\*(.+?):\*\*\s*(.+)$/);
  if (boldMatch) return { label: boldMatch[1], value: boldMatch[2] };
  const plainMatch = body.match(/^([A-Za-z ]+):\s*(.+)$/);
  if (plainMatch) return { label: plainMatch[1], value: plainMatch[2].replace(/`/g, "") };
  return { label: "", value: body };
}
function _parseFormulaExplanationBlocks(text) {
  if (!text) return [];
  const blocks = text.trim().split(/\n{2,}/).map((b) => b.trim()).filter(Boolean);
  const parsed = [];
  for (const block of blocks) {
    const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) continue;
    const titleMatch = lines[0].match(/^❌\s*\*\*(.+?)\*\*\s*$/);
    if (titleMatch && lines.length === 1) {
      parsed.push({ type: "title", text: titleMatch[1] });
      continue;
    }
    if (lines.every((l) => l.startsWith("- "))) {
      parsed.push({ type: "stats", items: lines.map(_parseFormulaBulletItem) });
      continue;
    }
    const headerOnlyMatch = lines[0].match(/^\*\*(.+?):\*\*$/);
    if (headerOnlyMatch && lines.length > 1 && lines.slice(1).every((l) => l.startsWith("- "))) {
      parsed.push({ type: "location", heading: headerOnlyMatch[1], items: lines.slice(1).map(_parseFormulaBulletItem) });
      continue;
    }
    const inlineFixMatch = block.match(/^\*\*How to fix:\*\*\s*([\s\S]+)$/i);
    if (inlineFixMatch) {
      parsed.push({ type: "fix", text: inlineFixMatch[1].trim() });
      continue;
    }
    if (lines.length === 1 && /round/i.test(lines[0])) {
      parsed.push({ type: "note", text: lines[0] });
      continue;
    }
    parsed.push({ type: "paragraph", text: block });
  }
  return parsed;
}
function _splitEmphasis(text, terms, ops) {
  const marks = [
    ...(terms || []).map((t) => ({ t, cls: "error-card-term" })),
    ...(ops || []).map((t) => ({ t, cls: "error-card-op" }))
  ].filter((m) => m.t && m.t.length > 1);
  if (marks.length === 0) return [text];
  marks.sort((a, b) => b.t.length - a.t.length);
  const pattern = marks.map((m) => m.t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  const classOf = new Map(marks.map((m) => [m.t.toLowerCase(), m.cls]));
  return text.split(new RegExp(`(${pattern})`, "g")).filter((piece) => piece !== "").map((piece) => {
    const cls = classOf.get(piece.toLowerCase());
    return cls ? { text: piece, cls } : piece;
  });
}
function RichText({ text, terms, ops }) {
  const parts = useMemo2(
    () => _splitEmphasis(text || "", terms, ops),
    [text, terms, ops]
  );
  return /* @__PURE__ */ h(F, null, parts.map(
    (p, i) => typeof p === "string" ? p : /* @__PURE__ */ h("span", { key: i, className: p.cls }, p.text)
  ));
}
var _MATRIX_STATUS = {
  ok: { glyph: "\u2713", className: "error-card-row-ok" },
  bad: { glyph: "\u2717", className: "error-card-row-bad" },
  unknown: { glyph: "?", className: "error-card-row-unknown" },
  neutral: { glyph: "", className: "" }
};
function ErrorCardMatrix({ section }) {
  const t = useT();
  const cols = section.columns || {};
  const rows = section.rows || [];
  if (rows.length === 0) return null;
  return /* @__PURE__ */ h("div", { className: "formula-error-section" }, section.heading && /* @__PURE__ */ h("div", { className: "formula-error-section-heading" }, section.heading), /* @__PURE__ */ h("div", { className: "error-card-matrix-scroll" }, /* @__PURE__ */ h("table", { className: "error-card-matrix" }, /* @__PURE__ */ h("thead", null, /* @__PURE__ */ h("tr", null, /* @__PURE__ */ h("th", { className: "error-card-matrix-status", "aria-label": t("common.status") }), /* @__PURE__ */ h("th", { className: "error-card-matrix-label" }, cols.label || t("errors.columns.item")), /* @__PURE__ */ h("th", { className: "error-card-matrix-expected" }, cols.expected || t("errors.columns.expected")), /* @__PURE__ */ h("th", { className: "error-card-matrix-actual" }, cols.actual || t("errors.columns.actual")))), /* @__PURE__ */ h("tbody", null, rows.map((r, i) => {
    const status = _MATRIX_STATUS[r.status] || _MATRIX_STATUS.neutral;
    return /* @__PURE__ */ h(
      "tr",
      {
        key: i,
        className: [
          status.className,
          // The result row of a formula is the consequence of the
          // rows above it, not a peer — it gets a rule above and
          // bolder text.
          r.emphasis ? "error-card-row-emphasis" : ""
        ].filter(Boolean).join(" ")
      },
      /* @__PURE__ */ h("td", { className: "error-card-matrix-status" }, status.glyph),
      /* @__PURE__ */ h("td", { className: "error-card-matrix-label" }, r.label),
      /* @__PURE__ */ h("td", { className: "error-card-matrix-expected" }, r.expected ? /* @__PURE__ */ h("span", { className: "error-card-matrix-num" }, r.expected) : /* @__PURE__ */ h("span", { className: "error-card-matrix-empty" }, "\u2014")),
      /* @__PURE__ */ h("td", { className: "error-card-matrix-actual" }, /* @__PURE__ */ h("span", { className: "error-card-matrix-num" }, r.actual), r.note && /* @__PURE__ */ h("em", { className: "error-card-matrix-note" }, r.note))
    );
  })))));
}
var _CARD_KINDS = ["locator", "matrix", "fix", "details"];
function FormulaErrorSections({ sections }) {
  if (!Array.isArray(sections) || sections.length === 0) return null;
  const isCard = sections.some((s) => _CARD_KINDS.includes(s.kind));
  return /* @__PURE__ */ h("div", { className: isCard ? "formula-error-body error-card-body" : "formula-error-body" }, sections.map((s, i) => {
    switch (s.kind) {
      case "headline":
        return /* @__PURE__ */ h("h4", { key: i, className: "formula-error-title" }, "\u274C ", /* @__PURE__ */ h(RichText, { text: s.text, terms: s.terms, ops: s.ops }));
      case "locator":
        return /* @__PURE__ */ h("div", { key: i, className: "formula-error-section error-card-locator" }, /* @__PURE__ */ h("div", { className: "formula-error-section-heading" }, s.heading), /* @__PURE__ */ h("div", { className: "formula-error-kv-grid" }, (s.items || []).map((it, j) => /* @__PURE__ */ h("div", { key: j, className: "formula-error-kv-row" }, it.label && /* @__PURE__ */ h("span", { className: "formula-error-kv-label" }, it.label, ":"), /* @__PURE__ */ h("span", { className: "formula-error-kv-value" }, it.value && it.value.includes("\n") ? /* @__PURE__ */ h("span", { className: "formula-error-kv-sublines" }, it.value.split("\n").map((line, k) => {
          const sep = line.indexOf(": ");
          const subLabel = sep >= 0 ? line.slice(0, sep) : "";
          const subValue = sep >= 0 ? line.slice(sep + 2) : line;
          return /* @__PURE__ */ h("div", { key: k, className: "formula-error-kv-subline" }, subLabel && /* @__PURE__ */ h("span", { className: "formula-error-kv-subline-label" }, subLabel), /* @__PURE__ */ h("span", { className: "formula-error-kv-subline-value" }, subValue));
        })) : it.mono ? /* @__PURE__ */ h("code", null, it.value) : it.value)))));
      case "matrix":
        return /* @__PURE__ */ h(ErrorCardMatrix, { key: i, section: s });
      case "fix":
        return /* @__PURE__ */ h("div", { key: i, className: "formula-error-section formula-error-fix" }, /* @__PURE__ */ h("div", { className: "formula-error-section-heading" }, s.heading), /* @__PURE__ */ h("ul", { className: "formula-error-points" }, (s.steps || []).map((step, j) => /* @__PURE__ */ h("li", { key: j }, /* @__PURE__ */ h(RichText, { text: step, terms: s.terms, ops: s.ops })))));
      case "details":
        return /* @__PURE__ */ h("details", { key: i, className: "error-card-details" }, /* @__PURE__ */ h("summary", { className: "error-card-details-summary" }, s.heading), /* @__PURE__ */ h("div", { className: "error-card-details-body" }, /* @__PURE__ */ h(FormulaErrorSections, { sections: s.sections })));
      case "rule":
        return (
          // error-card-rule is a spacing hook only. It is applied
          // unconditionally, but the CSS targets it as a DIRECT child of
          // .error-card-body — so a rule section nested in the details
          // drawer (or a legacy v1 body) is unaffected.
          /* @__PURE__ */ h("div", { key: i, className: "formula-error-section error-card-rule" }, s.heading && /* @__PURE__ */ h("div", { className: "formula-error-section-heading" }, s.heading), s.mono ? /* @__PURE__ */ h("code", { className: "formula-error-mono-block" }, s.text) : /* @__PURE__ */ h("p", { className: "formula-error-rule-text" }, !s.heading && "i.e. ", /* @__PURE__ */ h(RichText, { text: s.text, terms: s.terms, ops: s.ops })))
        );
      case "labeled_text":
        return /* @__PURE__ */ h("div", { key: i, className: "formula-error-section error-card-rule" }, /* @__PURE__ */ h("div", { className: "formula-error-section-heading" }, s.heading), s.mono ? /* @__PURE__ */ h("code", { className: "formula-error-mono-block" }, s.text) : /* @__PURE__ */ h("p", { className: "formula-error-rule-text" }, /* @__PURE__ */ h(RichText, { text: s.text, terms: s.terms, ops: s.ops })));
      case "values":
        return /* @__PURE__ */ h("div", { key: i, className: "formula-error-section" }, /* @__PURE__ */ h("div", { className: "formula-error-section-heading" }, s.heading), /* @__PURE__ */ h("div", { className: "formula-error-kv-grid" }, (s.items || []).map((it, j) => /* @__PURE__ */ h("div", { key: j, className: "formula-error-kv-row" }, it.label && /* @__PURE__ */ h("span", { className: "formula-error-kv-label" }, it.label, ":"), /* @__PURE__ */ h("span", { className: "formula-error-kv-value" }, it.value, it.note && /* @__PURE__ */ h("em", { className: "formula-error-kv-note" }, " (", it.note, ")"), it.context && /* @__PURE__ */ h("code", { className: "formula-error-kv-context", title: it.context }, it.context))))));
      case "points":
        return /* @__PURE__ */ h(
          "div",
          {
            key: i,
            className: /fix/i.test(s.heading || "") ? "formula-error-section formula-error-fix" : "formula-error-section"
          },
          /* @__PURE__ */ h("div", { className: "formula-error-section-heading" }, s.heading),
          /* @__PURE__ */ h("ul", { className: "formula-error-points" }, (s.bullets || []).map((b, j) => /* @__PURE__ */ h("li", { key: j }, /* @__PURE__ */ h(RichText, { text: b, terms: s.terms, ops: s.ops }))))
        );
      case "note":
        return /* @__PURE__ */ h("p", { key: i, className: "formula-error-note" }, s.text);
      default:
        return null;
    }
  }));
}
function FormulaErrorContent({ explanation }) {
  const t = useT();
  const blocks = useMemo2(() => _parseFormulaExplanationBlocks(explanation), [explanation]);
  if (blocks.length === 0) return null;
  return /* @__PURE__ */ h("div", { className: "formula-error-body" }, blocks.map((b, i) => {
    switch (b.type) {
      case "title":
        return /* @__PURE__ */ h("h4", { key: i, className: "formula-error-title" }, "\u274C ", b.text);
      case "paragraph":
        return /* @__PURE__ */ h("p", { key: i, className: "formula-error-explanation" }, b.text);
      case "note":
        return /* @__PURE__ */ h("p", { key: i, className: "formula-error-note" }, b.text);
      case "stats":
        return /* @__PURE__ */ h("div", { key: i, className: "formula-error-stats-grid" }, b.items.map((it, j) => /* @__PURE__ */ h("div", { key: j, className: "formula-error-stat" }, /* @__PURE__ */ h("span", { className: "formula-error-stat-label" }, it.label), /* @__PURE__ */ h("span", { className: "formula-error-stat-value" }, it.value))));
      case "location":
        return /* @__PURE__ */ h("div", { key: i, className: "formula-error-location" }, /* @__PURE__ */ h("div", { className: "formula-error-location-heading" }, b.heading), /* @__PURE__ */ h("div", { className: "formula-error-kv-grid" }, b.items.map((it, j) => /* @__PURE__ */ h("div", { key: j, className: "formula-error-kv-row" }, /* @__PURE__ */ h("span", { className: "formula-error-kv-label" }, it.label), /* @__PURE__ */ h("code", { className: "formula-error-kv-value" }, it.value)))));
      case "fix":
        return /* @__PURE__ */ h("div", { key: i, className: "formula-error-fix" }, /* @__PURE__ */ h("div", { className: "formula-error-fix-heading" }, t("errors.howToFix")), /* @__PURE__ */ h("p", { className: "formula-error-fix-text" }, b.text));
      default:
        return null;
    }
  }));
}
function PlainTextErrorPanel({ details, errorMessages, downloadUrl, downloadLabel }) {
  const t = useT();
  const groups = useMemo2(() => {
    const map = /* @__PURE__ */ new Map();
    const push_item = (item) => {
      const cat = item._error_category || "unknown";
      const section = item.section || item.rule_name || "";
      const key = `${cat}||${section}`;
      if (!map.has(key)) {
        map.set(key, { cat, meta: _catMeta(cat), sectionName: section, items: [] });
      }
      const group = map.get(key);
      if (group.items.length < 5) group.items.push(item);
    };
    if (Array.isArray(details) && details.length > 0) {
      for (const err of details) {
        if (err?.rule_name !== void 0) {
          const rawExplanation = err.explanation || err.business_rule || t("errors.validationRuleFailed").replace("{0}", err.rule_name);
          push_item({
            _error_category: err._error_category || "formula_error",
            section: err.rule_name,
            explanation: rawExplanation.replace(/^⚙\s*Formula Error\s*—[^\n]*\n+/, ""),
            // Structured sections built by backend/tools/formula_error.py.
            // Preferred over parsing `explanation` back out of a string; the
            // string remains the fallback for any producer that predates it.
            sections: Array.isArray(err.explanation_sections) ? err.explanation_sections : null,
            raw_message: err.business_rule || ""
          });
          continue;
        }
        push_item({
          _error_category: err._error_category || "unknown",
          section: err.section || "",
          explanation: err.explanation || err.message || "",
          raw_message: err.message || err.col_0 || ""
        });
      }
    }
    if (map.size === 0 && Array.isArray(errorMessages) && errorMessages.length > 0) {
      const group = { cat: "unknown", meta: _catMeta("unknown"), sectionName: "", items: [] };
      for (const msg of errorMessages.slice(0, 2)) {
        group.items.push({ explanation: msg, raw_message: "" });
      }
      map.set("fallback", group);
    }
    return [...map.values()];
  }, [details, errorMessages]);
  if (groups.length === 0) return null;
  return /* @__PURE__ */ h("div", { className: "error-panel-wrapper" }, groups.map((group, gi) => {
    const color = group.meta.color;
    const isFormula = group.cat === "formula_error";
    return /* @__PURE__ */ h("div", { key: gi, className: isFormula ? "formula-error-card" : "error-section-group" }, /* @__PURE__ */ h(
      "div",
      {
        className: isFormula ? "formula-error-card-header" : "error-section-header",
        style: isFormula ? void 0 : { "--section-color": color, background: color }
      },
      /* @__PURE__ */ h("span", { className: "section-icon" }, group.meta.icon),
      /* @__PURE__ */ h("span", { className: "section-name" }, group.meta.label, group.sectionName ? ` \u2014 ${group.sectionName}` : "")
    ), group.items.map((item, ii) => /* @__PURE__ */ h(
      "div",
      {
        key: ii,
        className: isFormula ? "formula-error-card-body" : "error-explanation-box",
        style: isFormula ? void 0 : { "--section-color": color, borderLeftColor: color }
      },
      item.explanation && (isFormula ? item.sections ? /* @__PURE__ */ h(FormulaErrorSections, { sections: item.sections }) : /* @__PURE__ */ h(FormulaErrorContent, { explanation: item.explanation }) : /* @__PURE__ */ h("p", { className: "error-explanation-text" }, item.explanation)),
      item.raw_message && item.raw_message !== item.explanation && /* @__PURE__ */ h("p", { className: "error-explanation-raw", title: item.raw_message }, item.raw_message)
    )));
  }), downloadUrl && /* @__PURE__ */ h("div", { className: "error-details-actions" }, /* @__PURE__ */ h(
    DownloadButton,
    {
      downloadUrl,
      downloadLabel,
      className: "error-details-dl-btn"
    }
  )));
}
var _DIM_SECTION_META = {
  "Dimension Error": { icon: "\u{1F4D0}", cls: "dim-sec-title" },
  "What is wrong": { icon: "\u26A0\uFE0F", cls: "dim-sec-wrong" },
  "What should be checked": { icon: "\u{1F50D}", cls: "dim-sec-check" },
  "Reported value": { icon: "\u{1F522}", cls: "dim-sec-value" },
  "Context": { icon: "\u{1F4CD}", cls: "dim-sec-context" }
};
var _DIM_SECTION_I18N = {
  "Dimension Error": "errors.category.dimensionalError",
  "What is wrong": "errors.whatIsWrong",
  "What should be checked": "errors.whatShouldBeChecked",
  "Reported value": "errors.reportedValue",
  "Context": "errors.columns.context"
};
function _parseDimensionSections(text) {
  if (!text) return null;
  const re = /\*\*([^*]+?):\*\*\s*([\s\S]*?)(?=\n\n\*\*[^*]+?:\*\*|$)/g;
  const sections = [];
  let m;
  while ((m = re.exec(text)) !== null) {
    const label = m[1].trim();
    const content = m[2].trim();
    if (label && content) sections.push({ label, content });
  }
  return sections.length ? sections : null;
}
function _renderInlineCode(text, keyPrefix) {
  return text.split("`").map(
    (part, i) => i % 2 === 1 ? /* @__PURE__ */ h("code", { key: `${keyPrefix}-${i}` }, part) : /* @__PURE__ */ h(React.Fragment, { key: `${keyPrefix}-${i}` }, part)
  );
}
function _renderBoldText(text, keyPrefix) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) => {
    const m = /^\*\*([^*]+)\*\*$/.exec(part);
    return m ? /* @__PURE__ */ h("strong", { key: `${keyPrefix}-${i}` }, m[1]) : /* @__PURE__ */ h(React.Fragment, { key: `${keyPrefix}-${i}` }, part);
  });
}
function DimensionalErrorPanel({ details, downloadUrl, downloadLabel }) {
  const t = useT();
  if (!details || details.length === 0) return null;
  const color = _catMeta("dimensional").color;
  return /* @__PURE__ */ h("div", { className: "error-panel-wrapper" }, /* @__PURE__ */ h("div", { className: "error-section-group" }, /* @__PURE__ */ h(
    "div",
    {
      className: "error-section-header",
      style: { "--section-color": color, background: color }
    },
    /* @__PURE__ */ h("span", { className: "section-icon" }, "\u{1F4D0}"),
    /* @__PURE__ */ h("span", { className: "section-name" }, t("errors.dimensionalTitle")),
    /* @__PURE__ */ h("span", { className: "error-section-count" }, details.length)
  ), /* @__PURE__ */ h("ol", { className: "dimensional-error-list" }, details.map((err, i) => {
    const structured = Array.isArray(err.explanation_sections) ? err.explanation_sections : null;
    const sections = structured ? null : _parseDimensionSections(err.explanation);
    return /* @__PURE__ */ h("li", { key: i, className: "dimensional-error-item" }, structured ? /* @__PURE__ */ h(FormulaErrorSections, { sections: structured }) : sections ? /* @__PURE__ */ h("div", { className: "dimensional-error-sections" }, sections.map((sec, si) => {
      const meta = _DIM_SECTION_META[sec.label] || { icon: "\u2022", cls: "dim-sec-generic" };
      return /* @__PURE__ */ h("div", { key: si, className: `dim-sec ${meta.cls}` }, /* @__PURE__ */ h("span", { className: "dim-sec-label" }, meta.icon, " ", _DIM_SECTION_I18N[sec.label] ? t(_DIM_SECTION_I18N[sec.label]) : sec.label, ":"), " ", /* @__PURE__ */ h("span", { className: "dim-sec-content" }, _renderInlineCode(sec.content, `s${i}-${si}`)));
    })) : /* @__PURE__ */ h("div", { className: "dimensional-error-explanation error-explanation-markdown" }, /* @__PURE__ */ h(ReactMarkdown, null, err.explanation || t("errors.dimensionalDetected").replace("{0}", err.concept || t("errors.unknownConcept")))), !structured && (err.concept || err.value || err.context) && /* @__PURE__ */ h("div", { className: "dimensional-error-meta" }, err.concept && /* @__PURE__ */ h("span", { className: "dim-meta-chip" }, "concept: ", err.concept), err.value && /* @__PURE__ */ h("span", { className: "dim-meta-chip" }, "value: ", err.value), err.context && /* @__PURE__ */ h("span", { className: "dim-meta-chip dim-meta-context", title: err.context }, "context: ", err.context.length > 40 ? err.context.slice(0, 40) + "\u2026" : err.context)));
  })), downloadUrl && /* @__PURE__ */ h("div", { className: "error-details-actions" }, /* @__PURE__ */ h(DownloadButton, { downloadUrl, downloadLabel, className: "error-details-dl-btn" }))));
}
function ErrorDetailsTablePanel({ details, downloadUrl, downloadLabel, errorMessages }) {
  const t = useT();
  const tableRows = useMemo2(() => details.map((err, i) => {
    const ti = err?.table_info ?? {};
    const db_table_name = (ti.db_table_name || err.db_tablename || err["db_tablename"] || err.table || "").toString().trim();
    const row_label = (ti.row_label || err.row_label || err["row_label(s)"] || err["row_label(s) "] || "").toString().trim();
    const context = (ti.context || err.context || "").toString().trim();
    const cell_code = (ti.cell_code || err.cellCode || err.cell || "").toString().trim();
    const validation_error = (ti.validation_error || err.message || err.col_0 || err.title || "").toString().trim();
    const explanation = (err.explanation || "").toString().trim();
    return { idx: i, db_table_name, row_label, context, cell_code, validation_error, explanation };
  }), [details]);
  const filteredRows = tableRows.filter(
    (r) => r.db_table_name || r.row_label || r.context || r.cell_code || r.validation_error
  );
  const hasBacktrackedData = filteredRows.some(
    (r) => r.db_table_name || r.row_label || r.cell_code
  );
  const explanationCell = (explanation) => explanation ? /* @__PURE__ */ h("ul", null, explanation.split(/(?<=[.!?])\s+/).filter(Boolean).map((point, i) => /* @__PURE__ */ h("li", { key: i }, _renderBoldText(point, `exp-${i}`)))) : "\u2014";
  return /* @__PURE__ */ h("div", { className: "error-details-panel" }, /* @__PURE__ */ h("div", { className: "error-table-info-section" }, /* @__PURE__ */ h("div", { className: "error-table-info-heading" }, "\u{1F4CB} Validation Details"), /* @__PURE__ */ h("div", { className: "error-table-info-scroll" }, /* @__PURE__ */ h("table", { className: `error-table-info-tbl${hasBacktrackedData ? "" : " error-table-info-tbl--compact"}` }, /* @__PURE__ */ h("thead", null, hasBacktrackedData ? /* @__PURE__ */ h("tr", null, /* @__PURE__ */ h("th", null, t("errors.columns.dbTableName")), /* @__PURE__ */ h("th", null, t("errors.columns.rowLabel")), /* @__PURE__ */ h("th", null, t("errors.columns.cellCode")), /* @__PURE__ */ h("th", null, t("errors.columns.error")), /* @__PURE__ */ h("th", null, t("errors.columns.explanation"))) : /* @__PURE__ */ h("tr", null, /* @__PURE__ */ h("th", null, t("errors.columns.error")), /* @__PURE__ */ h("th", null, t("errors.columns.explanation")))), /* @__PURE__ */ h("tbody", null, filteredRows.map((r) => hasBacktrackedData ? /* @__PURE__ */ h("tr", { key: r.idx }, /* @__PURE__ */ h("td", { title: r.db_table_name }, r.db_table_name || "\u2014"), /* @__PURE__ */ h("td", { title: r.row_label }, r.row_label || "\u2014"), /* @__PURE__ */ h("td", null, r.cell_code || "\u2014"), /* @__PURE__ */ h("td", { className: "vd-error-cell", title: r.explanation || r.validation_error }, r.validation_error || "\u2014"), /* @__PURE__ */ h("td", { className: "vd-explanation-cell" }, explanationCell(r.explanation))) : /* @__PURE__ */ h("tr", { key: r.idx }, /* @__PURE__ */ h("td", { className: "vd-error-cell", title: r.explanation || r.validation_error }, r.validation_error || "\u2014"), /* @__PURE__ */ h("td", { className: "vd-explanation-cell" }, explanationCell(r.explanation)))))))), /* @__PURE__ */ h("div", { className: "error-details-actions" }, /* @__PURE__ */ h(DownloadButton, { downloadUrl, downloadLabel, className: "error-details-dl-btn" })));
}
function ErrorDetailsPanel({ details, errorMessages, downloadUrl, downloadLabel }) {
  if ((!details || details.length === 0) && (!errorMessages || errorMessages.length === 0)) {
    return /* @__PURE__ */ h(DownloadButton, { downloadUrl, downloadLabel });
  }
  const category = detectErrorCategory(details);
  if (category === "xbrl_schema_4000") {
    return /* @__PURE__ */ h(
      ErrorDetailsTablePanel,
      {
        details,
        errorMessages,
        downloadUrl,
        downloadLabel
      }
    );
  }
  if (category === "dimensional") {
    return /* @__PURE__ */ h(
      DimensionalErrorPanel,
      {
        details,
        downloadUrl,
        downloadLabel
      }
    );
  }
  return /* @__PURE__ */ h(
    PlainTextErrorPanel,
    {
      details,
      errorMessages,
      downloadUrl,
      downloadLabel
    }
  );
}
function renderInlineBold(line, keyPrefix) {
  return String(line ?? "").split(/\*\*(.+?)\*\*/g).map(
    (part, i) => i % 2 === 1 ? /* @__PURE__ */ h("strong", { key: `${keyPrefix}-${i}` }, part) : part
  );
}
function renderValueLines(text) {
  const lines = String(text ?? "").split("\n");
  return lines.map((line, i) => {
    const m = line.includes("**") ? null : line.match(/^(.*?\S\s*:\s+)(\S.*)$/);
    return /* @__PURE__ */ h("span", { key: i }, m ? /* @__PURE__ */ h(F, null, m[1], /* @__PURE__ */ h("strong", null, m[2])) : renderInlineBold(line, i), i < lines.length - 1 && /* @__PURE__ */ h("br", null));
  });
}
function BubbleText({ text, errorDetails, boldValues = false }) {
  const t = useT();
  const FAILURE_HEADING = "Failure Reason(s):";
  const PENDING_MARKER = "Generating error explanations\u2026";
  const idx = (text ?? "").indexOf(FAILURE_HEADING);
  if ((text ?? "").includes(PENDING_MARKER) && (!errorDetails || errorDetails.length === 0)) {
    const beforePending = (text ?? "").replace(PENDING_MARKER, "").trimEnd();
    return /* @__PURE__ */ h(F, null, beforePending.split("\n").map((line, i, arr) => /* @__PURE__ */ h("span", { key: `b${i}` }, renderInlineBold(line, `b${i}`), i < arr.length - 1 && /* @__PURE__ */ h("br", null))), /* @__PURE__ */ h("br", null), /* @__PURE__ */ h("span", { className: "explanation-pending" }, "\u23F3 Generating error explanations\u2026"));
  }
  if (idx === -1) {
    if (boldValues) return renderValueLines(text);
    return (text ?? "").split("\n").map((line, i, arr) => /* @__PURE__ */ h("span", { key: i }, renderInlineBold(line, i), i < arr.length - 1 && /* @__PURE__ */ h("br", null)));
  }
  const before = (text ?? "").slice(0, idx).replace(/\n+$/, "");
  const failureBlock = (text ?? "").slice(idx);
  const structuredItems = (() => {
    if (!Array.isArray(errorDetails) || errorDetails.length === 0) return [];
    const items = [];
    const seen = /* @__PURE__ */ new Set();
    for (const err of errorDetails) {
      if (err?.rule_name !== void 0) {
        const msg = (err.explanation || t("errors.ruleFailed").replace("{0}", err.rule_name)).trim();
        if (msg && !seen.has(msg)) {
          seen.add(msg);
          items.push({ cellCode: "", message: msg, label: msg });
        }
        if (items.length >= 5) break;
        continue;
      }
      const ti = err?.table_info ?? {};
      const cellCode = (ti.cell_code || err.cellCode || err.cell || "").trim();
      const rawMsg = (err.explanation || ti.validation_error || err.message || err.col_0 || err.title || "").trim();
      if (!rawMsg) continue;
      const label = cellCode ? `${cellCode} \u2192 ${rawMsg}` : rawMsg;
      if (!seen.has(label)) {
        seen.add(label);
        items.push({ cellCode, message: rawMsg, label });
      }
      if (items.length >= 5) break;
    }
    return items;
  })();
  const failureLines = failureBlock.split("\n");
  const bulletEnd = failureLines.reduce((last, line, i) => line.startsWith("\u2022") ? i : last, 0);
  const rawBulletItems = structuredItems.length > 0 ? [] : failureLines.slice(1, bulletEnd + 1).map((l) => l.replace(/^•\s*/, "").trim()).filter(Boolean);
  const afterLines = failureLines.slice(bulletEnd + 1).filter((l) => l.trim());
  return /* @__PURE__ */ h(F, null, before.split("\n").map((line, i, arr) => /* @__PURE__ */ h("span", { key: `b${i}` }, line, i < arr.length - 1 && /* @__PURE__ */ h("br", null))), before && /* @__PURE__ */ h("br", null), /* @__PURE__ */ h("div", { className: "failure-reason-box" }, /* @__PURE__ */ h("div", { className: "failure-reason-heading" }, "\u26A0 Failure Reason(s)")), afterLines.map((line, i) => /* @__PURE__ */ h("span", { key: `a${i}` }, /* @__PURE__ */ h("br", null), line)));
}
var _MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function ScheduleDateTimePicker({ onSubmit }) {
  const t = useT();
  const pad = (n) => String(n).padStart(2, "0");
  const now = /* @__PURE__ */ new Date();
  const todayIso = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  const [date, setDate] = useState2("");
  const [time, setTime] = useState2("");
  const [clockOpen, setClockOpen] = useState2(false);
  const timeWrapRef = useRef2(null);
  const timeValid = /^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/.test(time);
  const timeHms = timeValid && time.length === 5 ? `${time}:00` : time;
  const notInFuture = Boolean(date) && timeValid && /* @__PURE__ */ new Date(`${date}T${timeHms}`) <= /* @__PURE__ */ new Date();
  const canSubmit = Boolean(date) && timeValid && !notInFuture;
  const timeParts = timeValid ? timeHms.split(":") : ["", "", ""];
  const pickPart = (idx, value) => {
    const parts = [timeParts[0] || "00", timeParts[1] || "00", timeParts[2] || "00"];
    parts[idx] = value;
    setTime(parts.join(":"));
  };
  useEffect2(() => {
    if (!clockOpen) return void 0;
    const onDown = (e) => {
      if (timeWrapRef.current && !timeWrapRef.current.contains(e.target)) setClockOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setClockOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    timeWrapRef.current?.querySelectorAll(".sched-time-opt.sel").forEach((el) => {
      const list = el.parentElement;
      list.scrollTop = el.offsetTop - list.clientHeight / 2 + el.clientHeight / 2;
    });
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [clockOpen]);
  const submit = () => {
    if (!canSubmit) return;
    const [y, m, d] = date.split("-");
    onSubmit?.(`${d}-${_MONTH_ABBR[Number(m) - 1]}-${y} at ${timeHms}`);
  };
  return /* @__PURE__ */ h("div", { className: "sched-picker" }, /* @__PURE__ */ h("label", { className: "sched-picker-field" }, /* @__PURE__ */ h("span", null, t("schedule.pickDate")), /* @__PURE__ */ h("input", { type: "date", value: date, min: todayIso, onChange: (e) => setDate(e.target.value) })), /* @__PURE__ */ h("label", { className: "sched-picker-field" }, /* @__PURE__ */ h("span", null, t("schedule.pickTime")), /* @__PURE__ */ h("span", { className: "sched-picker-time", ref: timeWrapRef }, /* @__PURE__ */ h(
    "input",
    {
      type: "text",
      readOnly: true,
      autoComplete: "off",
      maxLength: 8,
      placeholder: "HH:MM:SS",
      value: time,
      onClick: () => setClockOpen((o) => !o),
      "aria-label": t("schedule.pickTime"),
      "aria-haspopup": "dialog",
      "aria-expanded": clockOpen
    }
  ), /* @__PURE__ */ h("button", { type: "button", className: "sched-picker-clock", onClick: () => setClockOpen((o) => !o), "aria-label": t("schedule.pickTime") }, /* @__PURE__ */ h("svg", { width: "16", height: "16", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": "true" }, /* @__PURE__ */ h("circle", { cx: "12", cy: "12", r: "9" }), /* @__PURE__ */ h("polyline", { points: "12 7 12 12 15 14" }))), clockOpen && /* @__PURE__ */ h("div", { className: "sched-time-pop", role: "dialog", "aria-label": t("schedule.pickTime") }, /* @__PURE__ */ h("div", { className: "sched-time-cols" }, [["HH", 24], ["MM", 60], ["SS", 60]].map(([label, count], idx) => /* @__PURE__ */ h("div", { className: "sched-time-col", key: label }, /* @__PURE__ */ h("div", { className: "sched-time-col-h" }, label), /* @__PURE__ */ h("div", { className: "sched-time-list" }, Array.from({ length: count }, (_, i) => pad(i)).map((v) => /* @__PURE__ */ h(
    "button",
    {
      type: "button",
      key: v,
      className: `sched-time-opt${timeParts[idx] === v ? " sel" : ""}`,
      onClick: () => pickPart(idx, v)
    },
    v
  )))))), /* @__PURE__ */ h("button", { type: "button", className: "sched-time-done", onClick: () => setClockOpen(false) }, t("schedule.done"))))), /* @__PURE__ */ h("button", { type: "button", className: "suggestion-chip chip-confirm", disabled: !canSubmit, onClick: submit }, t("schedule.setSchedule")), notInFuture && /* @__PURE__ */ h("div", { className: "sched-picker-error" }, t("schedule.mustBeFuture")));
}
function MessageBubble({
  role,
  text,
  data,
  options,
  resultType,
  reportName,
  sqlData,
  dbQaData,
  varianceData,
  varianceAll,
  varianceMeta,
  labelA,
  labelB,
  llmSummary,
  summaryIsDraft,
  instancesData,
  downloadUrl,
  downloadLabel,
  errorDetails,
  errorMessages,
  feedbackQuery,
  feedbackIntent,
  onSuggestion,
  onGuidedAction,
  onCompare,
  onFeedback,
  onExplainCategory,
  batchCategory,
  batchErrorFilePath,
  batchFormId,
  batchReportName,
  allowedActions,
  noAutoSummary,
  onSummaryLoaded,
  lang,
  onLanguageChange,
  loginId,
  tenantId,
  domain,
  jwtRef
}) {
  const t = useT();
  const API_BASE = "";
  const isUser = role === "user";
  const isError = role === "error";
  const isWelcome = role === "welcome";
  if (isWelcome) return /* @__PURE__ */ h(WelcomeCard, { onSuggestion, onGuidedAction, allowedActions, lang, onLanguageChange });
  if (role === "action_menu") return /* @__PURE__ */ h(ActionMenu, { onGuidedAction, allowedActions, lang, onLanguageChange });
  if (role === "sql_welcome") return /* @__PURE__ */ h(SqlWelcomeCard, null);
  if (role === "feedback_prompt") return /* @__PURE__ */ h(
    FeedbackPrompt,
    {
      onFeedback,
      query: feedbackQuery,
      intent: feedbackIntent,
      resultType
    }
  );
  if (role === "feedback_positive") {
    return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h("div", { className: "bubble assistant-bubble" }, t("feedback.thanksPositive")));
  }
  if (role === "feedback_negative") return /* @__PURE__ */ h(SupportContact, null);
  if (!isUser && resultType === "guided_menu") {
    return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h(GuidedMenuCard, { text, options, onSelect: onSuggestion }));
  }
  if (!isUser && resultType === "guided_input") {
    return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h("div", { className: "assistant-msg-block" }, /* @__PURE__ */ h("div", { className: "bubble assistant-bubble guided-prompt-bubble" }, /* @__PURE__ */ h("span", { className: "guided-prompt-label" }, t("guidedBadge")), (text ?? "").split("\n").map((line, i, arr) => /* @__PURE__ */ h("span", { key: i }, line, i < arr.length - 1 && /* @__PURE__ */ h("br", null)))), options?.length > 0 && /* @__PURE__ */ h("div", { className: "welcome-suggestions option-chips" }, options.map((opt) => /* @__PURE__ */ h("button", { key: opt, className: "suggestion-chip", onClick: () => onSuggestion?.(opt) }, t.option(opt))))));
  }
  if (!isUser && resultType === "db_result" && sqlData) {
    return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h(SqlResultBlock, { data: sqlData }));
  }
  if (!isUser && resultType === "db_qa_result") {
    return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h(DbQaResultBlock, { data: dbQaData, fallbackText: text }));
  }
  if (!isUser && resultType === "date_selection" && options?.length > 0) {
    return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h(
      InstanceDropdown,
      {
        headerText: text,
        options,
        instancesData,
        onSelect: onSuggestion
      }
    ));
  }
  if (!isUser && resultType === "instance_selection" && instancesData?.length > 0) {
    return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h(
      InstanceSelectionBlock,
      {
        instances: instancesData,
        headerText: text,
        onCompare
      }
    ));
  }
  if (!isUser && resultType === "variance_table" && varianceData?.length > 0) {
    return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h(
      VarianceTableBlock,
      {
        rows: varianceData,
        allRows: varianceAll,
        meta: varianceMeta,
        labelA,
        labelB,
        llmSummary,
        summaryIsDraft,
        headerText: text,
        reportName,
        noAutoSummary,
        onSummaryLoaded,
        loginId,
        tenantId,
        domain,
        jwtRef
      }
    ));
  }
  const chips = options?.length > 0 ? options : [];
  const displayText = chips.length > 0 ? (text ?? "").split("\n").filter((l) => !/^\s*\d+\.\s/.test(l)).join("\n").replace(/\n{3,}/g, "\n\n").trim() : text ?? "";
  const resolvedErrorDetails = (Array.isArray(errorDetails) && errorDetails.length > 0 ? errorDetails : null) || (Array.isArray(data?.error_details) && data.error_details.length > 0 ? data.error_details : null) || (Array.isArray(data?.errorDetails) && data.errorDetails.length > 0 ? data.errorDetails : null) || [];
  const resolvedErrorMessages = (Array.isArray(errorMessages) && errorMessages.length > 0 ? errorMessages : null) || (Array.isArray(data?.error_messages) && data.error_messages.length > 0 ? data.error_messages : null) || [];
  const errorCategoryCounts = data?.error_category_counts ?? null;
  const is4000Series = data?.is_4000_series ?? false;
  const statusCode = data?.status_code ?? null;
  const isFailed = statusCode != null && FAILED_STATUS_CODES.has(Number(statusCode));
  const errorPanel = (() => {
    if (resolvedErrorDetails.length > 0) {
      return /* @__PURE__ */ h(
        ErrorDetailsPanel,
        {
          details: resolvedErrorDetails,
          errorMessages: resolvedErrorMessages,
          downloadUrl,
          downloadLabel
        }
      );
    }
    const hasErrorCounts = errorCategoryCounts && _CAT_ORDER.some((cat) => errorCategoryCounts[cat] > 0);
    if (isFailed && errorCategoryCounts && (hasErrorCounts || downloadUrl)) {
      return /* @__PURE__ */ h(
        ErrorSummaryPanel,
        {
          counts: errorCategoryCounts,
          downloadUrl,
          downloadLabel,
          onExplainCategory,
          formId: data?.form_id,
          reportName: data?.report_name,
          explainableCategories: is4000Series ? ["formula_error", "xbrl_schema", "dimensional"] : ["formula_error", "dimensional"]
        }
      );
    }
    if (resolvedErrorMessages.length > 0) {
      return /* @__PURE__ */ h(
        PlainTextErrorPanel,
        {
          details: [],
          errorMessages: resolvedErrorMessages,
          downloadUrl,
          downloadLabel
        }
      );
    }
    if (downloadUrl) {
      return /* @__PURE__ */ h(DownloadButton, { downloadUrl, downloadLabel });
    }
    return null;
  })();
  if (!isUser && resultType === "ask_previous") {
    return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h("div", { className: "assistant-msg-block" }, /* @__PURE__ */ h("div", { className: "bubble assistant-bubble" }, /* @__PURE__ */ h(BubbleText, { text: displayText, errorDetails: resolvedErrorDetails })), errorPanel, /* @__PURE__ */ h("div", { className: "bubble assistant-bubble", style: { marginTop: 6, fontStyle: "italic", fontSize: "0.88em" } }, t("checkAnotherDate")), /* @__PURE__ */ h("div", { className: "welcome-suggestions option-chips sched-confirm-actions" }, chips.map((opt) => /* @__PURE__ */ h(
      "button",
      {
        key: opt,
        className: `suggestion-chip${opt === "Yes" ? " chip-confirm" : " chip-cancel"}`,
        onClick: () => onSuggestion?.(opt)
      },
      t.option(opt)
    )))));
  }
  if (!isUser && resultType === "sched_awaiting_dt") {
    return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h("div", { className: "assistant-msg-block" }, /* @__PURE__ */ h("div", { className: "bubble assistant-bubble" }, displayText.split("\n").map((line, i, arr) => /* @__PURE__ */ h("span", { key: i }, renderInlineBold(line, i), i < arr.length - 1 && /* @__PURE__ */ h("br", null)))), /* @__PURE__ */ h(ScheduleDateTimePicker, { onSubmit: onSuggestion })));
  }
  if (!isUser && resultType === "sched_confirm") {
    return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h("div", { className: "assistant-msg-block" }, /* @__PURE__ */ h("div", { className: "bubble assistant-bubble sched-confirm-bubble" }, renderValueLines(displayText)), /* @__PURE__ */ h("div", { className: "welcome-suggestions option-chips sched-confirm-actions" }, chips.map((opt) => /* @__PURE__ */ h(
      "button",
      {
        key: opt,
        className: `suggestion-chip${opt === "Schedule" ? " chip-confirm" : " chip-cancel"}`,
        onClick: () => onSuggestion?.(opt)
      },
      t.option(opt)
    )))));
  }
  return /* @__PURE__ */ h("div", { className: `bubble-row ${isUser ? "user" : "assistant"}` }, !isUser && /* @__PURE__ */ h("div", { className: `avatar ${isError ? "error-avatar" : "assistant-avatar"}` }, isError ? "!" : "AI"), /* @__PURE__ */ h("div", { className: "assistant-msg-block" }, /* @__PURE__ */ h("div", { className: `bubble ${isUser ? "user-bubble" : isError ? "error-bubble" : "assistant-bubble"}` }, /* @__PURE__ */ h(
    BubbleText,
    {
      text: isUser ? t.echo(displayText) : displayText,
      errorDetails: resolvedErrorDetails,
      boldValues: !isUser && resultType === "schedule_parsed"
    }
  )), !isUser && chips.length > 0 && (chips.length >= 5 ? /* @__PURE__ */ h(ReportSearchDropdown, { options: chips, onSelect: onSuggestion }) : resultType === "sched_awaiting_rpt_date" ? (
    // Suggested reporting dates: one row of equal tabs spanning the
    // same width as the message above.
    /* @__PURE__ */ h("div", { className: "option-chips option-chips-row", style: { gridTemplateColumns: `repeat(${chips.length}, 1fr)` } }, chips.map((opt) => /* @__PURE__ */ h("button", { key: opt, className: "suggestion-chip", onClick: () => onSuggestion?.(opt) }, t.option(opt))))
  ) : /* @__PURE__ */ h("div", { className: "welcome-suggestions option-chips" }, chips.map((opt) => /* @__PURE__ */ h("button", { key: opt, className: "suggestion-chip", onClick: () => onSuggestion?.(opt) }, t.option(opt))))), !isUser && resultType !== "ask_previous" && errorPanel, !isUser && resultType === "final" && data?.has_more && batchCategory && /* @__PURE__ */ h(
    ExplainNextErrorsButton,
    {
      category: batchCategory,
      errorFilePath: batchErrorFilePath,
      formId: batchFormId,
      reportName: batchReportName,
      nextOffset: data?.next_offset ?? 0,
      onExplainCategory
    }
  )), isUser && /* @__PURE__ */ h("div", { className: "avatar user-avatar" }, t("common.you")));
}
function getStatusMeta(code) {
  const n = parseInt(code, 10);
  if (n === 11) return { label: "Approval Pending", color: "#00C853" };
  if (n === 9) return { label: "Approved", color: "#006400" };
  if ([3, 5, 8, 10, 13].includes(n)) return { label: "Failed", color: "#FF4D4F" };
  if (n === 12) return { label: "Rejected", color: "#C62828" };
  if (n === 4) return { label: "Extracted", color: "#29B6F6" };
  if (n === 6 || n === 1) return { label: "In Process", color: "#FF9800" };
  if (n === 2) return { label: "Extraction Started", color: "#FFA726" };
  if (n === 0) return { label: "In Queue", color: "#FFD600" };
  if (n === 20) return { label: "Deleted", color: "#9E9E9E" };
  if (n === 30) return { label: "Not Processed", color: "#B0BEC5" };
  return { label: "Unknown", color: "#9E9E9E" };
}
var STATUS_LEGEND = [11, 9, 12, 6, 4, 0, 3].map((code) => getStatusMeta(code));
function InstanceDropdown({ headerText, options, instancesData, onSelect }) {
  const t = useT();
  const [selected, setSelected] = useState2(options[0] ?? "");
  const statusMap = useMemo2(() => {
    if (!instancesData?.length) return {};
    return Object.fromEntries(
      instancesData.map((item) => [item.label, getStatusMeta(item.status)])
    );
  }, [instancesData]);
  const hasStatus = instancesData?.length > 0;
  return /* @__PURE__ */ h("div", { className: "assistant-msg-block" }, /* @__PURE__ */ h("div", { className: "bubble assistant-bubble" }, headerText), /* @__PURE__ */ h("div", { className: "instance-listbox-card" }, /* @__PURE__ */ h("div", { className: "instance-listbox" }, options.map((opt) => {
    const meta = hasStatus ? statusMap[opt] : null;
    return /* @__PURE__ */ h(
      "div",
      {
        key: opt,
        className: `instance-listbox-item${selected === opt ? " selected" : ""}`,
        onClick: () => setSelected(opt)
      },
      meta && /* @__PURE__ */ h("span", { className: "status-dot", style: { background: meta.color }, title: meta.label }),
      /* @__PURE__ */ h("span", { className: "instance-listbox-label" }, opt)
    );
  })), /* @__PURE__ */ h("button", { className: "instance-dropdown-btn", onClick: () => onSelect?.(selected) }, t("common.select"), " \u203A"), hasStatus && /* @__PURE__ */ h(StatusLegend, null)));
}
function StatusLegend() {
  const t = useT();
  return /* @__PURE__ */ h("div", { className: "status-legend", role: "note" }, /* @__PURE__ */ h("span", { className: "status-legend-title" }, "Status"), STATUS_LEGEND.map((meta) => /* @__PURE__ */ h("span", { className: "status-legend-item", key: meta.label }, /* @__PURE__ */ h("span", { className: "status-dot", style: { background: meta.color } }), meta.label)));
}
var SUGGESTION_GROUPS = [
  { icon: "\u{1F4CB}", action: "Check report status" },
  { icon: "\u2699\uFE0F", action: "Generate instance for a report" },
  { icon: "\u{1F5D3}\uFE0F", action: "Schedule a report" },
  { icon: "\u{1F4CA}", action: "Perform comparative analysis" },
  { icon: "\u{1F5C4}\uFE0F", action: "Retrieve data from database" }
];
function renderRich(str) {
  return String(str).split("*").map(
    (part, i) => i % 2 === 1 ? /* @__PURE__ */ h("strong", { key: i }, part) : part
  );
}
function _visibleGroups(allowedActions) {
  if (!allowedActions) return SUGGESTION_GROUPS;
  return SUGGESTION_GROUPS.filter((g) => allowedActions.includes(g.action));
}
function WelcomeCard({ onSuggestion, onGuidedAction, allowedActions, lang, onLanguageChange }) {
  const t = useT();
  const groups = _visibleGroups(allowedActions);
  const items = [
    "welcomeItemStatus",
    "welcomeItemGenerate",
    "welcomeItemSchedule",
    "welcomeItemCompare",
    "welcomeItemDatabase",
    "welcomeItemErrors"
  ];
  return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h("div", { className: "bubble assistant-bubble welcome-bubble" }, /* @__PURE__ */ h("p", { className: "welcome-greeting" }, t("welcomeGreeting")), /* @__PURE__ */ h("p", { className: "welcome-subtext" }, t("welcomeHelp")), /* @__PURE__ */ h("ul", { className: "welcome-list" }, items.map((key) => /* @__PURE__ */ h("li", { key }, renderRich(t(key))))), /* @__PURE__ */ h("p", { className: "welcome-subtext" }, t("welcomeCta")), /* @__PURE__ */ h("div", { className: "welcome-suggestion-groups" }, groups.map((group) => /* @__PURE__ */ h("div", { key: group.action, className: "welcome-suggestion-group" }, /* @__PURE__ */ h(
    "button",
    {
      className: "welcome-group-label-btn",
      onClick: () => onGuidedAction?.(group.action),
      title: `${t("startGuidedFlow")}: ${t.action(group.action)}`
    },
    group.icon,
    " ",
    t.action(group.action),
    /* @__PURE__ */ h("span", { className: "welcome-group-arrow" }, "\u203A")
  ))))));
}
var FEEDBACK_TIMEOUT_MS = 6500;
function FeedbackPrompt({ onFeedback, query, intent, resultType }) {
  const t = useT();
  const [answered, setAnswered] = useState2(false);
  const [expired, setExpired] = useState2(false);
  useEffect2(() => {
    if (answered) return;
    const t2 = setTimeout(() => setExpired(true), FEEDBACK_TIMEOUT_MS);
    return () => clearTimeout(t2);
  }, [answered]);
  const handleClick = (response) => {
    if (answered) return;
    setAnswered(true);
    onFeedback?.(response, { query, intent, resultType });
  };
  if (expired) return null;
  return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h(
    "div",
    {
      className: `assistant-msg-block${answered ? "" : " feedback-timed"}`,
      style: answered ? void 0 : { "--feedback-timeout": `${FEEDBACK_TIMEOUT_MS}ms` }
    },
    /* @__PURE__ */ h("div", { className: "bubble assistant-bubble" }, t("wasThisHelpful")),
    !answered && /* @__PURE__ */ h(F, null, /* @__PURE__ */ h("div", { className: "feedback-actions" }, /* @__PURE__ */ h("button", { className: "feedback-btn feedback-yes", onClick: () => handleClick("yes") }, "\u{1F44D} Yes"), /* @__PURE__ */ h("button", { className: "feedback-btn feedback-no", onClick: () => handleClick("no") }, "\u{1F44E} No")), /* @__PURE__ */ h("div", { className: "feedback-timer", "aria-hidden": "true" }, /* @__PURE__ */ h("div", { className: "feedback-timer-fill" })))
  ));
}
function SupportContact() {
  const t = useT();
  return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h("div", { className: "bubble assistant-bubble support-contact-bubble" }, /* @__PURE__ */ h("p", { className: "support-sorry" }, t("support.sorry")), /* @__PURE__ */ h("p", { className: "support-desc" }, t("support.contact")), /* @__PURE__ */ h("div", { className: "support-emails" }, /* @__PURE__ */ h("a", { href: "mailto:support@company.com", className: "support-email-link" }, "\u{1F4E7} support@company.com"), /* @__PURE__ */ h("a", { href: "mailto:chatbot-support@company.com", className: "support-email-link" }, "\u{1F4E7} chatbot-support@company.com"))));
}
function ActionMenu({ onGuidedAction, allowedActions, lang, onLanguageChange }) {
  const t = useT();
  const groups = _visibleGroups(allowedActions);
  return /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h("div", { className: "bubble assistant-bubble action-menu-bubble" }, /* @__PURE__ */ h("p", { className: "action-menu-prompt" }, t("actionMenuPrompt")), /* @__PURE__ */ h("div", { className: "welcome-suggestion-groups" }, groups.map((group) => /* @__PURE__ */ h("div", { key: group.action, className: "welcome-suggestion-group" }, /* @__PURE__ */ h(
    "button",
    {
      className: "welcome-group-label-btn",
      onClick: () => onGuidedAction?.(group.action),
      title: `${t("startGuidedFlow")}: ${t.action(group.action)}`
    },
    group.icon,
    " ",
    t.action(group.action),
    /* @__PURE__ */ h("span", { className: "welcome-group-arrow" }, "\u203A")
  ))))));
}
function ReportSearchDropdown({ options, onSelect, placeholder }) {
  const t = useT();
  const ph = placeholder ?? t("selectReportName");
  const [query, setQuery] = useState2("");
  const [isOpen, setIsOpen] = useState2(false);
  const [selected, setSelected] = useState2(null);
  const containerRef = useRef2(null);
  const filtered = query.trim() ? options.filter((o) => o.toLowerCase().includes(query.toLowerCase())) : options;
  useEffect2(() => {
    function handleClick(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setIsOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);
  const handleChoose = (opt) => {
    setSelected(opt);
    setIsOpen(false);
    setQuery("");
    onSelect?.(opt);
  };
  return /* @__PURE__ */ h("div", { className: "rsd-wrapper", ref: containerRef }, /* @__PURE__ */ h(
    "div",
    {
      className: `rsd-control${isOpen ? " rsd-open" : ""}`,
      onClick: () => setIsOpen((o) => !o)
    },
    selected ? /* @__PURE__ */ h("span", { className: "rsd-value" }, selected) : /* @__PURE__ */ h("span", { className: "rsd-placeholder" }, ph),
    /* @__PURE__ */ h("span", { className: "rsd-arrow" }, isOpen ? "\u25B2" : "\u25BC")
  ), isOpen && /* @__PURE__ */ h("div", { className: "rsd-menu" }, /* @__PURE__ */ h("div", { className: "rsd-search-wrap" }, /* @__PURE__ */ h(
    "input",
    {
      autoFocus: true,
      className: "rsd-search",
      placeholder: t("typeToFilter"),
      value: query,
      onChange: (e) => setQuery(e.target.value),
      onClick: (e) => e.stopPropagation()
    }
  )), /* @__PURE__ */ h("ul", { className: "rsd-list" }, filtered.length === 0 ? /* @__PURE__ */ h("li", { className: "rsd-no-results" }, t("sql.noMatches")) : filtered.map((opt) => /* @__PURE__ */ h("li", { key: opt, className: "rsd-item", onClick: () => handleChoose(opt) }, opt)))));
}
function SqlResultBlock({ data }) {
  const t = useT();
  const {
    sql,
    is_valid,
    validation_reason,
    db_error,
    matched_tables = [],
    matched_columns = [],
    columns = [],
    rows = [],
    accuracy_hint = null,
    needs_more_info = false,
    more_info_hint = null
  } = data;
  return /* @__PURE__ */ h("div", { className: "sql-result-block" }, matched_tables.length > 0 && /* @__PURE__ */ h("div", null, /* @__PURE__ */ h("div", { className: "sql-result-label" }, t("sql.schemaMatch")), /* @__PURE__ */ h("div", { className: "sql-result-chips" }, matched_tables.map((t2) => /* @__PURE__ */ h("span", { key: t2, className: "sql-chip-table" }, t2)), matched_columns.slice(0, 6).map((c) => /* @__PURE__ */ h("span", { key: c, className: "sql-chip-col" }, c)), matched_columns.length > 6 && /* @__PURE__ */ h("span", { className: "sql-chip-col" }, "+", matched_columns.length - 6, " more"))), sql && /* @__PURE__ */ h("div", null, /* @__PURE__ */ h("div", { className: "sql-result-label" }, t("sql.generatedSql")), /* @__PURE__ */ h("pre", { className: "sql-result-sql-box" }, sql)), !is_valid && /* @__PURE__ */ h("div", { className: "sql-invalid-msg" }, "\u26A0 ", validation_reason || t("errors.sqlValidationFailed")), db_error && /* @__PURE__ */ h("div", { className: "sql-db-error" }, "\u26A0 A database error occurred. Please try again."), is_valid && !db_error && columns.length > 0 && /* @__PURE__ */ h("div", null, /* @__PURE__ */ h("div", { className: "sql-result-label" }, t("sql.queryResults")), /* @__PURE__ */ h("div", { className: "sql-table-wrapper" }, /* @__PURE__ */ h("table", { className: "sql-data-table" }, /* @__PURE__ */ h("thead", null, /* @__PURE__ */ h("tr", null, columns.map((col) => /* @__PURE__ */ h("th", { key: col }, col)))), /* @__PURE__ */ h("tbody", null, rows.map((row, ri) => /* @__PURE__ */ h("tr", { key: ri }, row.map((cell, ci) => /* @__PURE__ */ h("td", { key: ci }, cell === null ? /* @__PURE__ */ h("span", { className: "sql-null-val" }, "NULL") : String(cell)))))))), /* @__PURE__ */ h("div", { className: "sql-row-count" }, rows.length, " row", rows.length !== 1 ? "s" : "", " returned")), is_valid && !db_error && columns.length === 0 && /* @__PURE__ */ h("div", { className: "sql-db-error", style: { color: "var(--text-muted)", background: "transparent", border: "none" } }, t("sql.noRowsReturned")), accuracy_hint && /* @__PURE__ */ h("div", { className: "sql-accuracy-hint" }, "\u{1F4A1} ", accuracy_hint), needs_more_info && more_info_hint && /* @__PURE__ */ h("div", { className: "sql-more-info-hint" }, /* @__PURE__ */ h("strong", null, t("sql.needMoreDetail")), /* @__PURE__ */ h("br", null), more_info_hint));
}
function renderDbQaCell(col, value) {
  if ((col === "Status" || col === "status") && (value === "Active" || value === "Inactive")) {
    return /* @__PURE__ */ h("span", { className: `dbqa-status-pill ${value === "Active" ? "is-active" : "is-inactive"}` }, value);
  }
  return value ?? "\u2014";
}
var DBQA_PAGE_SIZE = 10;
function DbQaResultBlock({ data, fallbackText }) {
  const t = useT();
  const [page, setPage] = useState2(0);
  if (!data || data.records?.length === 0 && !data.summary) {
    return /* @__PURE__ */ h("div", { className: "bubble assistant-bubble" }, fallbackText || t("noDataFound"));
  }
  const {
    label,
    summary,
    cols = [],
    headers = [],
    records = [],
    is_count,
    tableNames = [],
    rowLabels = [],
    contexts = [],
    cellCodes = []
  } = data;
  if (records.length === 0) return /* @__PURE__ */ h("div", { className: "bubble assistant-bubble" }, summary || fallbackText);
  const hasStructuredMeta = tableNames.length || rowLabels.length || contexts.length || cellCodes.length;
  const totalPages = Math.max(1, Math.ceil(records.length / DBQA_PAGE_SIZE));
  const clampedPage = Math.min(page, totalPages - 1);
  const pageStart = clampedPage * DBQA_PAGE_SIZE;
  const pageEnd = Math.min(pageStart + DBQA_PAGE_SIZE, records.length);
  const showPagination = records.length > DBQA_PAGE_SIZE;
  const paginationEl = showPagination && /* @__PURE__ */ h("div", { className: "dbqa-pagination" }, /* @__PURE__ */ h(
    "button",
    {
      type: "button",
      className: "dbqa-page-btn",
      onClick: () => setPage((p) => Math.max(0, p - 1)),
      disabled: clampedPage === 0
    },
    "\u2039 ",
    t("prev")
  ), /* @__PURE__ */ h("span", { className: "dbqa-page-info" }, pageStart + 1, "\u2013", pageEnd, " / ", records.length, " ", t("records"), " \xB7 ", clampedPage + 1, " / ", totalPages), /* @__PURE__ */ h(
    "button",
    {
      type: "button",
      className: "dbqa-page-btn",
      onClick: () => setPage((p) => Math.min(totalPages - 1, p + 1)),
      disabled: clampedPage >= totalPages - 1
    },
    t("next"),
    " \u203A"
  ));
  if (hasStructuredMeta) {
    const pageIdxs = Array.from({ length: pageEnd - pageStart }, (_, i) => pageStart + i);
    return /* @__PURE__ */ h("div", { className: "dbqa-block structured-dbqa" }, label && /* @__PURE__ */ h("div", { className: "dbqa-header-row" }, /* @__PURE__ */ h("span", { className: "dbqa-label" }, label), /* @__PURE__ */ h("span", { className: "dbqa-record-count" }, records.length, " records")), /* @__PURE__ */ h("div", { className: "dbqa-table-wrapper" }, /* @__PURE__ */ h("table", { className: "dbqa-table" }, /* @__PURE__ */ h("thead", null, /* @__PURE__ */ h("tr", null, /* @__PURE__ */ h("th", null, t("errors.columns.dbTableName")), /* @__PURE__ */ h("th", null, t("errors.columns.rowLabels")), /* @__PURE__ */ h("th", null, t("errors.columns.context")), /* @__PURE__ */ h("th", null, t("errors.columns.cellCode")))), /* @__PURE__ */ h("tbody", null, pageIdxs.map((i) => /* @__PURE__ */ h("tr", { key: i }, /* @__PURE__ */ h("td", null, tableNames[i] ?? "\u2014"), /* @__PURE__ */ h("td", null, rowLabels[i] ?? "\u2014"), /* @__PURE__ */ h("td", null, contexts[i] ?? "\u2014"), /* @__PURE__ */ h("td", null, cellCodes[i] ?? "\u2014")))))), paginationEl, summary && /* @__PURE__ */ h("div", { className: "dbqa-summary" }, summary));
  }
  if (is_count) {
    const rec = records[0];
    return /* @__PURE__ */ h("div", { className: "dbqa-block" }, /* @__PURE__ */ h("div", { className: "dbqa-count-row" }, cols.map((c, i) => /* @__PURE__ */ h("div", { key: c, className: "dbqa-count-card" }, /* @__PURE__ */ h("div", { className: "dbqa-count-val" }, rec[c] ?? "\u2014"), /* @__PURE__ */ h("div", { className: "dbqa-count-label" }, headers[i])))), summary && /* @__PURE__ */ h("div", { className: "dbqa-summary" }, summary));
  }
  if (records.length === 1) {
    const rec = records[0];
    return /* @__PURE__ */ h("div", { className: "dbqa-block" }, /* @__PURE__ */ h("div", { className: "dbqa-kv-list" }, cols.map((c, i) => /* @__PURE__ */ h("div", { key: c, className: "dbqa-kv-row" }, /* @__PURE__ */ h("span", { className: "dbqa-kv-key" }, headers[i]), /* @__PURE__ */ h("span", { className: "dbqa-kv-val" }, renderDbQaCell(c, rec[c]))))));
  }
  const pageRecords = records.slice(pageStart, pageEnd);
  return /* @__PURE__ */ h("div", { className: "dbqa-block" }, label && /* @__PURE__ */ h("div", { className: "dbqa-header-row" }, /* @__PURE__ */ h("span", { className: "dbqa-label" }, label), /* @__PURE__ */ h("span", { className: "dbqa-record-count" }, records.length, " records")), /* @__PURE__ */ h("div", { className: "dbqa-table-wrapper" }, /* @__PURE__ */ h("table", { className: "dbqa-table" }, /* @__PURE__ */ h("thead", null, /* @__PURE__ */ h("tr", null, headers.map((h2) => /* @__PURE__ */ h2("th", { key: h2 }, h2)))), /* @__PURE__ */ h("tbody", null, pageRecords.map((rec, ri) => /* @__PURE__ */ h("tr", { key: pageStart + ri }, cols.map((c) => /* @__PURE__ */ h("td", { key: c }, renderDbQaCell(c, rec[c])))))))), paginationEl, summary && /* @__PURE__ */ h("div", { className: "dbqa-summary" }, summary));
}
function InstanceSelectionBlock({ instances, headerText, onCompare }) {
  const t = useT();
  const NONE = "";
  const [sel1, setSel1] = useState2(NONE);
  const [sel2, setSel2] = useState2(NONE);
  const [error, setError] = useState2("");
  const labelFor = (inst) => inst.label || `${inst.reporting_date || "\u2014"} | Generated: ${inst.run_at || "\u2014"}`;
  const handleCompare = () => {
    if (!sel1 || !sel2) {
      setError(t("variance.selectEachDropdown"));
      return;
    }
    if (sel1 === sel2) {
      setError(t("variance.chooseTwoInstances"));
      return;
    }
    setError("");
    onCompare?.(parseInt(sel1, 10) - 1, parseInt(sel2, 10) - 1);
  };
  return /* @__PURE__ */ h("div", { className: "inst-sel-block" }, /* @__PURE__ */ h("div", { className: "inst-sel-header" }, headerText), /* @__PURE__ */ h("div", { className: "inst-sel-dropdowns" }, /* @__PURE__ */ h("div", { className: "inst-sel-dropdown-group" }, /* @__PURE__ */ h("label", { className: "inst-sel-label" }, t("comparativeAnalysis.instance1")), /* @__PURE__ */ h("select", { className: "inst-sel-select", value: sel1, onChange: (e) => {
    setSel1(e.target.value);
    setError("");
  } }, /* @__PURE__ */ h("option", { value: "" }, t("variance.selectInstancePlaceholder")), instances.map((inst, idx) => /* @__PURE__ */ h("option", { key: idx, value: String(idx + 1) }, labelFor(inst))))), /* @__PURE__ */ h("div", { className: "inst-sel-dropdown-group" }, /* @__PURE__ */ h("label", { className: "inst-sel-label" }, t("comparativeAnalysis.instance2")), /* @__PURE__ */ h("select", { className: "inst-sel-select", value: sel2, onChange: (e) => {
    setSel2(e.target.value);
    setError("");
  } }, /* @__PURE__ */ h("option", { value: "" }, t("variance.selectInstancePlaceholder")), instances.map((inst, idx) => /* @__PURE__ */ h("option", { key: idx, value: String(idx + 1), disabled: String(idx + 1) === sel1 }, labelFor(inst)))))), error && /* @__PURE__ */ h("div", { className: "inst-sel-error" }, error), /* @__PURE__ */ h(
    "button",
    {
      className: "inst-sel-btn",
      disabled: !sel1 || !sel2 || sel1 === sel2,
      onClick: handleCompare
    },
    t("comparativeAnalysis.compareInstances")
  ));
}
var SEV_CFG = {
  critical: { label: "C", title: "Critical", cls: "vt-sev-critical" },
  high: { label: "H", title: "High", cls: "vt-sev-high" },
  medium: { label: "M", title: "Medium", cls: "vt-sev-medium" },
  low: { label: "L", title: "Low", cls: "vt-sev-low" }
};
var TIER_ORDER = ["Critical", "High", "Medium", "Low"];
function selectHeadlineTiers(sourceRows) {
  const counts = Object.fromEntries(TIER_ORDER.map((tier) => [tier, 0]));
  for (const r of sourceRows) {
    if (r.importance_matched && Object.prototype.hasOwnProperty.call(counts, r.importance_tier)) {
      counts[r.importance_tier] += 1;
    }
  }
  const topIdx = TIER_ORDER.findIndex((tier) => counts[tier] > 0);
  if (topIdx === -1) return [];
  return TIER_ORDER.slice(topIdx, topIdx + 2);
}
function fmtFinancial2(v) {
  if (v === null || v === void 0) return "\u2014";
  if (v === 0) return "0";
  const abs = Math.abs(v);
  if (abs >= 1e12) return `${(v / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(v / 1e3).toFixed(2)}K`;
  if (abs >= 1) return v.toFixed(2);
  if (abs >= 1e-3) return v.toFixed(4);
  const places = Math.min(10, Math.max(4, Math.ceil(-Math.log10(abs)) + 3));
  return v.toFixed(places);
}
function fmtRaw2(v) {
  if (v === null || v === void 0) return "\u2014";
  return Number(v).toLocaleString(void 0, { maximumFractionDigits: 6 });
}
function fmtPctFin(v) {
  if (v === null || v === void 0) return "N/A";
  const abs = Math.abs(v);
  const sign = v > 0 ? "+" : v < 0 ? "-" : "";
  if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(2)}B%`;
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(2)}M%`;
  if (abs >= 1e3) return `${sign}${Math.round(abs).toLocaleString()}%`;
  return `${sign}${abs.toFixed(2)}%`;
}
function pctExactLabel(v, t) {
  if (v === null || v === void 0) return t("variance.noPctZeroBaseline");
  return `${t("comparativeAnalysis.exactChange")}: ${v >= 0 ? "+" : ""}${v.toLocaleString(void 0, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}%`;
}
function changeDir(diff) {
  const d = diff ?? 0;
  if (d > 0) return { cls: "vt-pos", arrow: "\u2191", sign: "+" };
  if (d < 0) return { cls: "vt-neg", arrow: "\u2193", sign: "" };
  return { cls: "vt-neutral", arrow: "\u2192", sign: "" };
}
function fmtSignedFin(v) {
  const d = v ?? 0;
  const body = fmtFinancial2(Math.abs(d));
  if (d > 0) return `+${body}`;
  if (d < 0) return `-${body}`;
  return "0";
}
var ROWCOUNT_OPTIONS = [10, 25, 50, 100, "All"];
var vtFilters = (t) => [
  ["all", t("common.all"), t("comparativeAnalysis.filters.allDesc")],
  ["sig", t("comparativeAnalysis.highVariance"), t("comparativeAnalysis.filters.sigDesc")],
  ["up", t("comparativeAnalysis.increased"), t("comparativeAnalysis.filters.upDesc")],
  ["down", t("comparativeAnalysis.decreased"), t("comparativeAnalysis.filters.downDesc")],
  ["reversal", t("comparativeAnalysis.reversed"), t("comparativeAnalysis.filters.reversalDesc")],
  [
    "zero",
    t("comparativeAnalysis.filters.zero"),
    t("comparativeAnalysis.zeroBaselineNote")
  ]
];
function VarianceTableBlock({ rows, allRows, meta, labelA, labelB, llmSummary, summaryIsDraft, headerText, reportName, noAutoSummary, onSummaryLoaded, loginId, tenantId, domain, jwtRef }) {
  const t = useT();
  const [showChart, setShowChart] = useState2(false);
  const [sortBy, setSortBy] = useState2(null);
  const [sortDir, setSortDir] = useState2("desc");
  const [rowCount, setRowCount] = useState2(ROWCOUNT_OPTIONS[0]);
  const [filterMode, setFilterMode] = useState2("all");
  const [search, setSearch] = useState2("");
  const sourceRows = allRows?.length ? allRows : rows;
  const importanceAvailable = Boolean(
    meta?.importance_available ?? sourceRows.some((r) => r.importance_matched)
  );
  const headlineTiers = useMemo2(() => selectHeadlineTiers(sourceRows), [sourceRows]);
  const headlineRows = useMemo2(
    () => sourceRows.filter(
      (r) => r.importance_matched && headlineTiers.includes(r.importance_tier)
    ),
    [sourceRows, headlineTiers]
  );
  const tableScope = importanceAvailable && headlineRows.length > 0 ? headlineRows : sourceRows;
  const summaryScope = useMemo2(
    () => importanceAvailable && headlineRows.length > 0 ? headlineRows : rows.slice(0, 40),
    [importanceAvailable, headlineRows, rows]
  );
  const lines = (headerText || "").split("\n");
  const title = lines[0] || "";
  const subtitle = lines[1] || "";
  const [asyncSummary, setAsyncSummary] = useState2("");
  const [summaryLoading, setSummaryLoading] = useState2(false);
  const summaryRequestedRef = useRef2(false);
  const summaryAbortRef = useRef2(null);
  const summaryRequestIdRef = useRef2(null);
  const summaryCancelledRef = useRef2(false);
  useEffect2(() => {
    const isDraft = typeof llmSummary === "string" && llmSummary.includes("\u2022") && summaryIsDraft;
    if (llmSummary && !isDraft || noAutoSummary) return void 0;
    if (!summaryScope?.length) {
      if (!summaryRequestedRef.current) {
        summaryRequestedRef.current = true;
        onSummaryLoaded?.("");
      }
      return void 0;
    }
    if (summaryRequestedRef.current) return void 0;
    summaryRequestedRef.current = true;
    const controller = new AbortController();
    summaryAbortRef.current = controller;
    const requestId = crypto?.randomUUID?.() ?? String(Date.now());
    summaryRequestIdRef.current = requestId;
    setSummaryLoading(true);
    const resolvedReportName = reportName || "";
    fetchCompareSummary(
      summaryScope,
      labelA,
      labelB,
      resolvedReportName,
      // t.lang is the active language from the shared LanguageContext -- no
      // second language state anywhere. tenantId/domain/jwt are the same
      // CHATBOT_AUTH-sourced values every other 6.0-aware call already
      // sends -- without them, login_id below can't be resolved against
      // the caller's own tenant and the endpoint 403s (see api.js).
      {
        signal: controller.signal,
        requestId,
        lang: t.lang,
        loginId,
        tenantId,
        domain,
        jwt: jwtRef?.current || null
      }
    ).then((text) => {
      if (summaryCancelledRef.current) return;
      setSummaryLoading(false);
      setAsyncSummary(text);
      onSummaryLoaded?.(text);
    });
    return void 0;
  }, [llmSummary, noAutoSummary]);
  const handleStopSummary = () => {
    summaryCancelledRef.current = true;
    summaryAbortRef.current?.abort();
    if (summaryRequestIdRef.current) stopRequest(summaryRequestIdRef.current);
    setSummaryLoading(false);
    onSummaryLoaded?.("");
  };
  const summaryText = llmSummary || asyncSummary;
  const SEV_ORDER = { critical: 4, high: 3, medium: 2, low: 1 };
  const filteredRows = useMemo2(() => {
    const q = search.trim().toLowerCase();
    const base = filterMode === "all" && !q ? tableScope : sourceRows;
    let out = base;
    if (filterMode === "sig") out = out.filter((r) => r.significant);
    else if (filterMode === "up") out = out.filter((r) => (r.diff ?? 0) > 0);
    else if (filterMode === "down") out = out.filter((r) => (r.diff ?? 0) < 0);
    else if (filterMode === "reversal") out = out.filter((r) => r.sign_change);
    else if (filterMode === "zero") {
      out = out.filter((r) => r.pct_change === null || r.pct_change === void 0);
    }
    if (q) out = out.filter((r) => `${r.concept ?? ""} ${r.concept_label ?? ""}`.toLowerCase().includes(q));
    return out;
  }, [tableScope, sourceRows, filterMode, search]);
  const sortedRows = useMemo2(() => {
    if (!sortBy) return filteredRows;
    const dir = sortDir === "asc" ? 1 : -1;
    const nullLast = (a, b, key) => {
      const av = key(a), bv = key(b);
      const aN = av === null || av === void 0;
      const bN = bv === null || bv === void 0;
      if (aN && bN) return 0;
      if (aN) return 1;
      if (bN) return -1;
      return dir * (av - bv);
    };
    return [...filteredRows].sort((a, b) => {
      if (sortBy === "concept") return dir * (a.concept ?? "").localeCompare(b.concept ?? "");
      if (sortBy === "val_a") return nullLast(a, b, (r) => r.val_a);
      if (sortBy === "val_b") return nullLast(a, b, (r) => r.val_b);
      if (sortBy === "diff") return dir * ((a.diff ?? 0) - (b.diff ?? 0));
      if (sortBy === "pct") return nullLast(a, b, (r) => r.pct_change === null || r.pct_change === void 0 ? null : Math.abs(r.pct_change));
      if (sortBy === "severity") return dir * ((SEV_ORDER[a.severity] ?? 0) - (SEV_ORDER[b.severity] ?? 0));
      return 0;
    });
  }, [filteredRows, sortBy, sortDir]);
  const visibleRows = useMemo2(
    () => rowCount === "All" ? sortedRows : sortedRows.slice(0, rowCount),
    [sortedRows, rowCount]
  );
  const isFiltered = filterMode !== "all" || Boolean(search.trim());
  const filterCounts = useMemo2(() => {
    let sig = 0, up = 0, down = 0, rev = 0, zero = 0;
    for (const r of sourceRows) {
      if (r.significant) sig++;
      if (r.sign_change) rev++;
      if (r.pct_change === null || r.pct_change === void 0) zero++;
      const d = r.diff ?? 0;
      if (d > 0) up++;
      else if (d < 0) down++;
    }
    return { all: sourceRows.length, sig, up, down, reversal: rev, zero };
  }, [sourceRows]);
  const handleSort = (col) => {
    if (sortBy === col) setSortDir((d) => d === "asc" ? "desc" : "asc");
    else {
      setSortBy(col);
      setSortDir("desc");
    }
  };
  const sortIcon = (col) => {
    if (sortBy !== col) return /* @__PURE__ */ h("span", { className: "vt-sort-icon" }, "\u21C5");
    return /* @__PURE__ */ h("span", { className: "vt-sort-icon" }, sortDir === "asc" ? "\u2191" : "\u2193");
  };
  return /* @__PURE__ */ h("div", { className: "variance-block" }, title && /* @__PURE__ */ h("div", { className: "variance-title" }, title), subtitle && /* @__PURE__ */ h("div", { className: "variance-subtitle" }, subtitle), importanceAvailable && headlineRows.length > 0 && headlineTiers[0] !== "Critical" && filterMode === "all" && !search.trim() && /* @__PURE__ */ h("div", { className: "variance-tier-note" }, "Showing ", headlineTiers.join(" + "), " concepts \u2014 no changes in ", TIER_ORDER.slice(0, TIER_ORDER.indexOf(headlineTiers[0])).join("/"), "."), /* @__PURE__ */ h("div", { className: "vt-controls" }, /* @__PURE__ */ h("div", { className: "vt-filter-group" }, vtFilters(t).map(([key, label, hint]) => {
    const n = filterCounts[key];
    return /* @__PURE__ */ h(
      "button",
      {
        key,
        className: `vt-chip${filterMode === key ? " active" : ""}`,
        onClick: () => setFilterMode(key),
        title: hint,
        type: "button"
      },
      label,
      n !== void 0 ? ` (${n.toLocaleString()})` : ""
    );
  })), /* @__PURE__ */ h("div", { className: "vt-controls-right" }, /* @__PURE__ */ h(
    "input",
    {
      className: "vt-search",
      type: "search",
      placeholder: t("comparativeAnalysis.searchConcept"),
      value: search,
      onChange: (e) => setSearch(e.target.value),
      "aria-label": t("comparativeAnalysis.filterTooltip"),
      title: t("comparativeAnalysis.filterNoteTable")
    }
  ), /* @__PURE__ */ h("div", { className: "vt-rowcount-group" }, /* @__PURE__ */ h("label", { className: "vt-rowcount-label", htmlFor: "vt-rowcount" }, t("common.rows")), /* @__PURE__ */ h(
    "select",
    {
      id: "vt-rowcount",
      className: "vt-select",
      value: String(rowCount),
      onChange: (e) => {
        const v = e.target.value;
        setRowCount(v === "All" ? "All" : Number(v));
      },
      title: t("comparativeAnalysis.rowsNoteTable")
    },
    ROWCOUNT_OPTIONS.map((opt) => /* @__PURE__ */ h("option", { key: String(opt), value: String(opt) }, opt === "All" ? t("comparativeAnalysis.allCount").replace("{0}", sortedRows.length.toLocaleString()) : opt))
  )))), /* @__PURE__ */ h("div", { className: "variance-table-wrapper" }, /* @__PURE__ */ h("table", { className: "variance-table" }, /* @__PURE__ */ h("thead", null, /* @__PURE__ */ h("tr", null, /* @__PURE__ */ h("th", { className: "vt-concept-col vt-sortable", onClick: () => handleSort("concept") }, t("comparativeAnalysis.columns.concept"), " ", sortIcon("concept")), /* @__PURE__ */ h("th", { className: "vt-num-col vt-sortable", onClick: () => handleSort("val_a") }, labelA, " ", sortIcon("val_a")), /* @__PURE__ */ h("th", { className: "vt-num-col vt-sortable", onClick: () => handleSort("val_b") }, labelB, " ", sortIcon("val_b")), /* @__PURE__ */ h("th", { className: "vt-num-col vt-sortable", onClick: () => handleSort("diff") }, t("comparativeAnalysis.columns.diff"), " ", sortIcon("diff")), /* @__PURE__ */ h("th", { className: "vt-num-col vt-sortable", onClick: () => handleSort("pct") }, t("comparativeAnalysis.columns.pctChange"), " ", sortIcon("pct")))), /* @__PURE__ */ h("tbody", null, visibleRows.map((row, rowIdx) => {
    const dir = changeDir(row.diff);
    const diffCls = dir.cls;
    const rowCls = [
      row.significant ? "vt-row-sig" : "",
      row.sign_change ? "vt-row-sign-change" : "",
      rowIdx % 2 === 0 ? "" : "vt-row-alt"
    ].filter(Boolean).join(" ");
    const anomalyText = row.anomaly_flags?.length ? `Anomalies: ${row.anomaly_flags.join(", ")}` : "";
    let memberSuffix = (row.concept ?? "").includes(" [") ? row.concept.slice(row.concept.indexOf(" [")) : "";
    if (memberSuffix && row.member_labels?.length) {
      const raw = memberSuffix.slice(2, -1).split(", ");
      if (raw.length === row.member_labels.length) {
        memberSuffix = ` [${raw.map((m, i) => row.member_labels[i] || m).join(", ")}]`;
      }
    }
    const conceptText = row.concept_label ? `${row.concept_label}${memberSuffix}` : row.concept ?? "";
    const conceptTitle = [
      row.concept_label ? `${conceptText} (${row.concept})` : row.concept,
      row.context_key && row.context_key !== "BASE" ? `Context: ${row.context_key}` : "",
      row.unit ? `Unit: ${row.unit}` : "",
      anomalyText
    ].filter(Boolean).join("\n");
    const unitLabel = row.unit ? ` ${row.unit}` : "";
    const tipA = `Raw: ${fmtRaw2(row.val_a)}${unitLabel}`;
    const tipB = `Raw: ${fmtRaw2(row.val_b)}${unitLabel}`;
    const tipD = `${t("comparativeAnalysis.rawDiff")}: ${fmtRaw2(row.diff)}${unitLabel}`;
    let signNote = null;
    if (row.sign_change) {
      const notation = (row.val_a ?? 0) > 0 ? "\u2212\u2192+" : "+\u2192\u2212";
      signNote = /* @__PURE__ */ h("span", { className: "vt-sign-note", title: `${t("comparativeAnalysis.directionReversedLabel")}: ${notation}` }, notation);
    }
    const isZeroBase = row.pct_change === null || row.pct_change === void 0;
    const sev = SEV_CFG[row.severity];
    const sevBadge = sev ? /* @__PURE__ */ h("span", { className: `vt-severity-badge ${sev.cls}`, title: `Severity: ${sev.title}` }, sev.label) : null;
    return /* @__PURE__ */ h("tr", { key: rowIdx, className: rowCls }, /* @__PURE__ */ h("td", { className: "vt-concept" }, row.significant && /* @__PURE__ */ h("span", { className: "vt-sig-badge", title: t("comparativeAnalysis.highVariance") }, "\u26A0"), /* @__PURE__ */ h("span", { className: "vt-concept-text", title: conceptTitle }, conceptText), signNote), /* @__PURE__ */ h("td", { className: "vt-num", title: tipA }, fmtFinancial2(row.val_a)), /* @__PURE__ */ h("td", { className: "vt-num", title: tipB }, fmtFinancial2(row.val_b)), /* @__PURE__ */ h("td", { className: "vt-num", title: tipD }, /* @__PURE__ */ h("span", { className: `vt-delta ${diffCls}` }, /* @__PURE__ */ h("span", { className: "vt-dir-arrow", "aria-hidden": "true" }, dir.arrow), fmtSignedFin(row.diff))), /* @__PURE__ */ h("td", { className: "vt-num" }, isZeroBase ? /* @__PURE__ */ h(
      "span",
      {
        className: "vt-pct vt-pct-zerobase",
        title: t("comparativeAnalysis.zeroBaseTooltip").replace("{0}", labelB)
      },
      "0 \u2192"
    ) : /* @__PURE__ */ h("span", { className: `vt-pct ${diffCls}`, title: pctExactLabel(row.pct_change, t) }, /* @__PURE__ */ h("span", { className: "vt-dot", "aria-hidden": "true" }), fmtPctFin(row.pct_change))));
  }), visibleRows.length === 0 && /* @__PURE__ */ h("tr", null, /* @__PURE__ */ h("td", { className: "vt-empty", colSpan: 5 }, importanceAvailable && headlineRows.length === 0 && !isFiltered ? /* @__PURE__ */ h(F, null, "No regulatory-importance concepts changed in this comparison. ", sourceRows.length.toLocaleString(), " concept(s) were compared \u2014 open ", /* @__PURE__ */ h("b", null, t("comparativeAnalysis.visualize")), " ", t("variance.toSeeEveryTier")) : /* @__PURE__ */ h(F, null, t("comparativeAnalysis.noFactsMatch")), isFiltered && /* @__PURE__ */ h(
    "button",
    {
      className: "vt-link-btn",
      onClick: () => {
        setFilterMode("all");
        setSearch("");
      },
      type: "button"
    },
    t("common.clearFilters")
  )))))), rowCount !== "All" && sortedRows.length > visibleRows.length && /* @__PURE__ */ h("div", { className: "vt-more" }, t("comparativeAnalysis.moreRowsNotShown").replace("{0}", (sortedRows.length - visibleRows.length).toLocaleString()), /* @__PURE__ */ h("button", { className: "vt-link-btn", onClick: () => setRowCount("All"), type: "button" }, t("comparativeAnalysis.showAll").replace("{0}", sortedRows.length.toLocaleString()))), /* @__PURE__ */ h("div", { className: "variance-summary" }, /* @__PURE__ */ h("div", { className: "variance-summary-header" }, /* @__PURE__ */ h("div", { className: "variance-summary-label" }, t("comparativeAnalysis.aiAnalysis"), summaryLoading && /* @__PURE__ */ h("span", { className: "variance-summary-status" }, /* @__PURE__ */ h("span", { className: "variance-summary-spinner", "aria-hidden": "true" }), "generating")), /* @__PURE__ */ h("div", { className: "variance-summary-actions" }, summaryLoading && /* @__PURE__ */ h(
    "button",
    {
      className: "vc-stop-btn",
      onClick: handleStopSummary,
      title: t("comparativeAnalysis.stopAnalysis")
    },
    "\u25A0 Stop"
  ), /* @__PURE__ */ h("button", { className: "vc-visualize-btn", onClick: () => setShowChart(true), title: t("comparativeAnalysis.openChart") }, "\u{1F4CA} Visualize"))), summaryText ? /* @__PURE__ */ h("div", { className: "variance-summary-text" }, /* @__PURE__ */ h(ReactMarkdown, null, summaryText.replace(/^AI\s+Summary:\s*/i, "").split("\n").map((l) => l.replace(/^•\s*/, "- ")).join("\n"))) : summaryLoading ? (
    // role/aria-live so a screen reader announces the wait rather than
    // landing on a panel that appears empty.
    /* @__PURE__ */ h(
      "div",
      {
        className: "variance-summary-text variance-summary-loading",
        role: "status",
        "aria-live": "polite"
      },
      /* @__PURE__ */ h("span", { className: "variance-summary-skeleton", "aria-hidden": "true" }, /* @__PURE__ */ h("i", null), /* @__PURE__ */ h("i", null), /* @__PURE__ */ h("i", null)),
      /* @__PURE__ */ h("span", { className: "variance-summary-loading-text" }, "Analysing the variance\u2026 this can take a minute or two. The table and chart above are ready now.")
    )
  ) : !summaryScope?.length ? (
    // Deliberately skipped (nothing eligible to summarize), not a
    // failed/timed-out call -- "unavailable" implies the latter and
    // reads as a malfunction when there's simply nothing to analyze.
    // Only reached when NO tier at all has a changed concept
    // (selectHeadlineTiers() already fell back through every lower
    // tier first).
    /* @__PURE__ */ h("div", { className: "variance-summary-text variance-summary-empty" }, "No regulatory-importance concepts changed, so there is nothing to analyse. The variance table and chart above are complete.")
  ) : /* @__PURE__ */ h("div", { className: "variance-summary-text variance-summary-empty" }, "AI analysis is unavailable for this comparison. The variance table and chart above are complete.")), showChart && /* @__PURE__ */ h(
    VarianceChartModal,
    {
      rows: allRows?.length ? allRows : rows,
      meta,
      labelA,
      labelB,
      summaryText,
      onClose: () => setShowChart(false)
    }
  ));
}
var GUIDED_ACTION_ICONS = {
  "Check report status": "\u{1F4CB}",
  "Generate instance for a report": "\u2699\uFE0F",
  "Schedule a report": "\u{1F5D3}\uFE0F",
  "Perform comparative analysis": "\u{1F4CA}",
  "Retrieve data from database": "\u{1F5C4}\uFE0F"
};
function GuidedMenuCard({ text, options, onSelect }) {
  const t = useT();
  return /* @__PURE__ */ h("div", { className: "guided-menu-card" }, /* @__PURE__ */ h("p", { className: "guided-menu-prompt" }, text), /* @__PURE__ */ h("div", { className: "guided-menu-options" }, (options || []).map((opt) => {
    const icon = GUIDED_ACTION_ICONS[opt] || "\u2022";
    const desc = t.actionDesc(opt);
    return /* @__PURE__ */ h("button", { key: opt, className: "guided-action-btn", onClick: () => onSelect?.(opt) }, /* @__PURE__ */ h("span", { className: "guided-action-icon" }, icon), /* @__PURE__ */ h("div", { className: "guided-action-body" }, /* @__PURE__ */ h("span", { className: "guided-action-label" }, t.action(opt)), desc && desc !== opt && /* @__PURE__ */ h("span", { className: "guided-action-desc" }, desc)), /* @__PURE__ */ h("span", { className: "guided-action-arrow" }, "\u203A"));
  })));
}

// src/components/ChatWindow.jsx
function ChatWindow({ messages, isLoading, onSuggestion, onGuidedAction, onCompare, onFeedback, onExplainCategory, onSummaryLoaded, allowedActions, lang, onLanguageChange, loginId, tenantId, domain, jwtRef }) {
  const bottomRef = useRef3(null);
  useEffect3(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);
  return /* @__PURE__ */ h("div", { className: "chat-window" }, messages.map((msg, idx) => /* @__PURE__ */ h(
    MessageBubble,
    {
      key: idx,
      role: msg.role,
      text: msg.text,
      data: msg.data,
      options: msg.options,
      resultType: msg.resultType,
      reportName: msg.reportName,
      feedbackQuery: msg.query,
      feedbackIntent: msg.intent,
      sqlData: msg.sqlData,
      dbQaData: msg.dbQaData,
      varianceData: msg.varianceData,
      varianceAll: msg.varianceAll,
      varianceMeta: msg.varianceMeta,
      labelA: msg.labelA,
      labelB: msg.labelB,
      llmSummary: msg.llmSummary,
      summaryIsDraft: msg.summaryIsDraft,
      noAutoSummary: msg.noAutoSummary,
      onSummaryLoaded: (text) => onSummaryLoaded?.(idx, text),
      instancesData: msg.instancesData,
      downloadUrl: msg.downloadUrl,
      downloadLabel: msg.downloadLabel,
      errorDetails: msg.errorDetails,
      jobId: msg.jobId,
      batchCategory: msg.batchCategory,
      batchErrorFilePath: msg.batchErrorFilePath,
      batchFormId: msg.batchFormId,
      batchReportName: msg.batchReportName,
      onSuggestion,
      onGuidedAction,
      onCompare,
      onFeedback,
      onExplainCategory: (cat, errorFilePath, formId, reportName, offset) => onExplainCategory?.(cat, errorFilePath, formId, reportName, offset),
      allowedActions,
      lang,
      onLanguageChange,
      loginId,
      tenantId,
      domain,
      jwtRef
    }
  )), isLoading && /* @__PURE__ */ h("div", { className: "bubble-row assistant" }, /* @__PURE__ */ h("div", { className: "avatar assistant-avatar" }, "AI"), /* @__PURE__ */ h("div", { className: "bubble assistant-bubble typing-indicator" }, /* @__PURE__ */ h("span", null), /* @__PURE__ */ h("span", null), /* @__PURE__ */ h("span", null))), /* @__PURE__ */ h("div", { ref: bottomRef }));
}

// src/components/VoiceInput.jsx
import { useState as useState3, useRef as useRef4, useCallback as useCallback3, useEffect as useEffect4 } from "react";
var MAX_SECONDS = 60;
var WARN_AT = 10;
function VoiceInput({ onTranscript, onStateChange, disabled }) {
  const t = useT();
  const [state, setState] = useState3("idle");
  const [error, setError] = useState3(null);
  const [remaining, setRemaining] = useState3(null);
  const mediaRecorderRef = useRef4(null);
  const chunksRef = useRef4([]);
  const timerRef = useRef4(null);
  const abortRef = useRef4(null);
  const requestIdRef = useRef4(null);
  const langRef = useRef4(t.lang);
  useEffect4(() => {
    langRef.current = t.lang;
  }, [t.lang]);
  useEffect4(() => {
    onStateChange?.(state);
  }, [state, onStateChange]);
  useEffect4(() => () => {
    if (timerRef.current) clearInterval(timerRef.current);
    abortRef.current?.abort();
  }, []);
  const startRecording = useCallback3(async () => {
    setError(null);
    chunksRef.current = [];
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      setError(t("voice.micRequired"));
      return;
    }
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "";
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
    mediaRecorderRef.current = recorder;
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.onstop = async () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setRemaining(null);
      stream.getTracks().forEach((t2) => t2.stop());
      const blob = new Blob(chunksRef.current, {
        type: recorder.mimeType || "audio/webm"
      });
      setState("processing");
      const controller = new AbortController();
      abortRef.current = controller;
      const requestId = crypto.randomUUID();
      requestIdRef.current = requestId;
      try {
        const transcript = await transcribeAudio(blob, {
          lang: langRef.current,
          signal: controller.signal,
          requestId
        });
        if (transcript) {
          onTranscript(transcript);
        } else {
          setError(t("voice.notHeard"));
        }
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(err.message || t("voice.transcribeFailed"));
        }
      } finally {
        abortRef.current = null;
        requestIdRef.current = null;
        setState("idle");
      }
    };
    recorder.start();
    setState("recording");
    let left = MAX_SECONDS;
    setRemaining(null);
    timerRef.current = setInterval(() => {
      left -= 1;
      setRemaining(left <= WARN_AT ? left : null);
      if (left <= 0) stopRecording();
    }, 1e3);
  }, [onTranscript]);
  const stopRecording = useCallback3(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }, []);
  const cancelTranscription = useCallback3(() => {
    abortRef.current?.abort();
    if (requestIdRef.current) stopRequest(requestIdRef.current);
  }, []);
  const handleClick = () => {
    if (state === "idle") startRecording();
    else if (state === "recording") stopRecording();
    else if (state === "processing") cancelTranscription();
  };
  const label = state === "recording" ? t("voice.stop") : state === "processing" ? t("voice.stopTranscribing") : t("voice.start");
  return /* @__PURE__ */ h("div", { className: "voice-input-wrapper" }, /* @__PURE__ */ h(
    "button",
    {
      type: "button",
      className: `mic-btn mic-btn--${state}`,
      onClick: handleClick,
      disabled,
      "aria-label": label,
      title: label
    },
    state === "processing" ? /* @__PURE__ */ h(StopSpinnerIcon, null) : /* @__PURE__ */ h(MicIcon, { active: state === "recording" })
  ), remaining !== null && state === "recording" && /* @__PURE__ */ h("span", { className: "mic-countdown", "aria-live": "polite" }, remaining, "s"), state === "processing" && /* @__PURE__ */ h("span", { className: "mic-processing", role: "status", "aria-live": "polite" }, t("voice.transcribing")), error && /* @__PURE__ */ h("span", { className: "mic-error" }, error));
}
function MicIcon({ active }) {
  return /* @__PURE__ */ h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ h("rect", { x: "9", y: "2", width: "6", height: "11", rx: "3", fill: active ? "currentColor" : "none" }), /* @__PURE__ */ h("path", { d: "M5 10a7 7 0 0 0 14 0" }), /* @__PURE__ */ h("line", { x1: "12", y1: "19", x2: "12", y2: "23" }), /* @__PURE__ */ h("line", { x1: "8", y1: "23", x2: "16", y2: "23" }));
}
function StopSpinnerIcon() {
  return /* @__PURE__ */ h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2" }, /* @__PURE__ */ h("g", { className: "spin", style: { transformOrigin: "12px 12px" } }, /* @__PURE__ */ h("circle", { cx: "12", cy: "12", r: "10", strokeOpacity: "0.3" }), /* @__PURE__ */ h("path", { d: "M12 2a10 10 0 0 1 10 10" })), /* @__PURE__ */ h("rect", { x: "9", y: "9", width: "6", height: "6", rx: "1", fill: "currentColor", stroke: "none" }));
}

// src/services/historyStorage.js
var DB_NAME = "chatbot-history";
var DB_VERSION = 1;
var STORE_NAME = "histories";
var LS_KEY_PREFIX = "chat_history_";
var MAX_STORED_MESSAGES = 200;
var _dbPromise = null;
function _openDatabase() {
  if (_dbPromise) return _dbPromise;
  _dbPromise = new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("IndexedDB is not available in this browser/context"));
      return;
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "historyId" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("IndexedDB open failed"));
    request.onblocked = () => reject(new Error("IndexedDB open blocked (another tab holds an older version)"));
  });
  _dbPromise.catch(() => {
    _dbPromise = null;
  });
  return _dbPromise;
}
function _runTransaction(mode, work) {
  return _openDatabase().then((db) => new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, mode);
    const store = tx.objectStore(STORE_NAME);
    let result;
    tx.oncomplete = () => resolve(result);
    tx.onerror = () => reject(tx.error || new Error("IndexedDB transaction failed"));
    tx.onabort = () => reject(tx.error || new Error("IndexedDB transaction aborted"));
    try {
      result = work(store);
    } catch (err) {
      reject(err);
    }
  }));
}
function _requestToPromise(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
function _migrateFromLocalStorage(historyId) {
  let raw;
  try {
    raw = localStorage.getItem(LS_KEY_PREFIX + historyId);
  } catch {
    return null;
  }
  if (!raw) return null;
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!Array.isArray(parsed) || parsed.length === 0) return null;
  return parsed;
}
async function loadHistory(historyId) {
  if (!historyId) return null;
  const existing = await _runTransaction("readonly", (store) => _requestToPromise(store.get(historyId)));
  if (existing) return existing.messages;
  const migrated = _migrateFromLocalStorage(historyId);
  if (!migrated) return null;
  await saveHistory(historyId, migrated);
  try {
    localStorage.removeItem(LS_KEY_PREFIX + historyId);
  } catch {
  }
  return migrated;
}
async function saveHistory(historyId, messages) {
  if (!historyId) return;
  const bounded = Array.isArray(messages) && messages.length > MAX_STORED_MESSAGES ? messages.slice(messages.length - MAX_STORED_MESSAGES) : messages;
  await _runTransaction("readwrite", (store) => _requestToPromise(store.put({ historyId, messages: bounded, updatedAt: Date.now() })));
}
async function deleteHistory(historyId) {
  if (!historyId) return;
  await _runTransaction("readwrite", (store) => _requestToPromise(store.delete(historyId)));
  try {
    localStorage.removeItem(LS_KEY_PREFIX + historyId);
  } catch {
  }
}

// src/App.jsx
var _TRUSTED_PARENT_ORIGINS = (import.meta.env && import.meta.env.VITE_TRUSTED_PARENT_ORIGINS || typeof window !== "undefined" && window.location && window.location.origin || "").split(",").map((s) => s.trim()).filter(Boolean);
function isTrustedParentMessage(event) {
  if (event.source !== window.parent) return false;
  return _TRUSTED_PARENT_ORIGINS.includes(event.origin);
}
var _params = new URLSearchParams(window.location.search);
function _readParam(urlKey, sessionKey) {
  const fromUrl = _params.get(urlKey) || "";
  if (fromUrl) {
    sessionStorage.setItem(sessionKey, fromUrl);
    try {
      localStorage.setItem(sessionKey, fromUrl);
    } catch {
    }
    return fromUrl;
  }
  return sessionStorage.getItem(sessionKey) || (() => {
    try {
      return localStorage.getItem(sessionKey) || "";
    } catch {
      return "";
    }
  })();
}
var _loginId = _readParam("loginId", "chat_loginId");
var _uid = _readParam("uid", "chat_uid");
var _roleId = _readParam("roleId", "chat_roleId") || _readParam("rid", "chat_rid") || "";
var _aspSession = _params.get("aspSession") || "";
var _langParam = _params.get("lang") || "";
var _tenantId = _readParam("tenant_id", "chat_tenant_id");
var _domain = _readParam("domain", "chat_domain");
var _jwt = _params.get("jwt") || "";
var _isV6 = Boolean(_tenantId);
if (_isV6) {
  Promise.resolve().then(() => __toESM(require_App_6_0()));
} else {
  Promise.resolve().then(() => __toESM(require_App_5_5()));
}
function _anonymousHistoryId() {
  const key = "chat_anon_uid";
  try {
    const existing = localStorage.getItem(key);
    if (existing) return existing;
    const fresh = `anon_${crypto.randomUUID()}`;
    localStorage.setItem(key, fresh);
    return fresh;
  } catch {
    return "anon_session";
  }
}
var _bareHistoryId = _loginId || _uid || _anonymousHistoryId();
var _historyId = _isV6 ? `${_tenantId}::${_bareHistoryId}` : _bareHistoryId;
function _getRecentHistory(messages, n = 7) {
  return messages.filter((m) => m.role === "user" || m.role === "assistant").map((m) => ({
    role: m.role,
    // Backend HistoryItem caps text at 2000 chars; a long variance reply
    // sent whole made every following /chat fail with a 422.
    text: (m.textEn || m.text || "").slice(0, 2e3)
  })).filter((m) => m.text).slice(-n);
}
function _markRestoredVarianceMessages(messages) {
  return messages.map((m) => m && m.resultType === "variance_table" ? { ...m, noAutoSummary: true } : m);
}
function App() {
  const [messages, setMessages] = useState4([{ role: "welcome" }]);
  const historyReadyRef = useRef5(false);
  useEffect5(() => {
    if (!_historyId) {
      historyReadyRef.current = true;
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const loaded = await loadHistory(_historyId);
        if (cancelled) return;
        if (Array.isArray(loaded) && loaded.length > 0) {
          setMessages(_markRestoredVarianceMessages(loaded));
        }
      } catch (e) {
        console.error("[CHAT_HISTORY] initial load from IndexedDB failed \u2014", e);
      } finally {
        if (!cancelled) historyReadyRef.current = true;
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);
  const [inputText, setInputText] = useState4("");
  const [voiceState, setVoiceState] = useState4("idle");
  const [lang, setLang] = useState4(() => {
    if (_langParam) return _langParam;
    try {
      return localStorage.getItem("chat_lang") || "en";
    } catch {
      return "en";
    }
  });
  useEffect5(() => {
    try {
      localStorage.setItem("chat_lang", lang);
    } catch {
    }
  }, [lang]);
  const [isLoading, setIsLoading] = useState4(false);
  const [isGuidedFlow, setIsGuidedFlow] = useState4(false);
  const inputRef = useRef5(null);
  const sessionId = useRef5(_uid || crypto.randomUUID());
  const pollIntervalRef = useRef5(null);
  const pendingFollowUpRef = useRef5(null);
  const activeRequestRef = useRef5(null);
  const jwtRef = useRef5(_jwt);
  useEffect5(() => {
    if (window.parent === window) return;
    function handleAuthMessage(event) {
      if (!event.data) return;
      if (!isTrustedParentMessage(event)) return;
      if (event.data.type === "CHATBOT_AUTH") {
        if (typeof event.data.jwt === "string" && event.data.jwt) {
          jwtRef.current = event.data.jwt;
        }
        return;
      }
      if (event.data.type === "CHATBOT_LANG") {
        if (typeof event.data.lang === "string" && event.data.lang) {
          setLang(event.data.lang);
        }
      }
    }
    window.addEventListener("message", handleAuthMessage);
    window.parent.postMessage({ type: "CHATBOT_READY" }, "*");
    return () => window.removeEventListener("message", handleAuthMessage);
  }, []);
  const [allowedActions, setAllowedActions] = useState4(null);
  useEffect5(() => {
    if (!_loginId) return;
    let cancelled = false;
    (async () => {
      try {
        const actions = await getAllowedActions(_loginId || null, {
          tenantId: _tenantId || null,
          domain: _domain || null
        });
        if (!cancelled && actions.length > 0) {
          setAllowedActions(actions);
        }
      } catch {
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);
  useEffect5(() => {
    if (!_historyId) return;
    if (!historyReadyRef.current) return;
    saveHistory(_historyId, messages).catch((e) => {
      console.error("[CHAT_HISTORY] save to IndexedDB failed \u2014", e);
    });
  }, [messages]);
  const handleClearChat = () => {
    deleteHistory(_historyId).catch((e) => console.error("[CHAT_HISTORY] clear failed \u2014", e));
    setMessages([{ role: "welcome" }]);
    setIsGuidedFlow(false);
  };
  useEffect5(() => {
    function handleLogoutMessage(event) {
      if (!event.data || event.data.type !== "CHATBOT_LOGOUT") return;
      if (!isTrustedParentMessage(event)) return;
      deleteHistory(_historyId).catch((e) => console.error("[CHAT_HISTORY] logout clear failed \u2014", e));
      for (const key of ["chat_uid", "chat_loginId", "chat_roleId", "chat_rid", "chat_tenant_id", "chat_domain", "chat_anon_uid"]) {
        try {
          sessionStorage.removeItem(key);
        } catch {
        }
        try {
          localStorage.removeItem(key);
        } catch {
        }
      }
      setMessages([{ role: "welcome" }]);
      setIsGuidedFlow(false);
    }
    window.addEventListener("message", handleLogoutMessage);
    return () => window.removeEventListener("message", handleLogoutMessage);
  }, []);
  const _TERMINAL_TYPES = /* @__PURE__ */ new Set([
    "final",
    // report status check done
    "variance_table",
    // comparative analysis done
    "gen_success",
    // report generation done
    "schedule_parsed",
    // scheduling confirmed
    "sql_result",
    // database query done
    "db_result",
    // SQL agent query done
    "db_qa_result"
    // XML App DB Q&A done
  ]);
  const _pushResult = (result, extra = {}) => {
    const isTerminal = _TERMINAL_TYPES.has(result.result_type);
    const jobId = result.job_id ?? result.jobId ?? result.job?.id ?? null;
    const _isSqlResult = result.result_type === "db_result";
    const _hasSqlContent = _isSqlResult && !!(result.db_sql || result.db_columns && result.db_columns.length > 0);
    const _sqlData = _hasSqlContent ? {
      sql: result.db_sql || "",
      is_valid: !result.db_error,
      validation_reason: result.db_error || "",
      db_error: result.db_error || null,
      columns: result.db_columns || [],
      rows: result.db_rows || [],
      matched_tables: [],
      matched_columns: [],
      accuracy_hint: result.accuracy_hint || null,
      needs_more_info: result.needs_more_info || false,
      more_info_hint: result.more_info_hint || null
    } : null;
    const resultMsg = {
      role: "assistant",
      text: result.response_text || result.text || "",
      // English source of this reply (empty unless multilingual is active).
      // Replayed as conversation_history so the backend always sees English.
      textEn: result?.data?.i18n?.english?.response_text || "",
      // Structured report name. The variance header is localized, so the name
      // must come from the field rather than be parsed out of the prose.
      reportName: result.report_name || "",
      data: result.data || null,
      options: result.options || [],
      resultType: result.result_type || "",
      sqlData: _sqlData,
      varianceData: result.variance_data || [],
      // Chart dataset — EVERY comparable row. Kept separate from varianceData
      // (the 30-row table slice) so the visualisation is never fed the table's
      // truncation. Falls back to varianceData only if an older backend omits it.
      varianceAll: result.variance_all || result.variance_data || [],
      varianceMeta: result.variance_meta || {},
      summaryIsDraft: Boolean(result.llm_summary_is_draft),
      // Variance rolled up into the return's own business sections, ranked by
      // the regulatory importance its taxonomy states. Empty for a return whose
      // taxonomy could not be read — the section panel then simply does not render.
      labelA: result.variance_label_a || "",
      labelB: result.variance_label_b || "",
      llmSummary: result.llm_summary || "",
      instancesData: result.instances_data || [],
      downloadUrl: result.download_url || "",
      downloadLabel: result.download_label || "",
      statusNote: result.status_note || "",
      dbQaData: result.db_qa_data || null,
      // Feedback context — carried forward onto the feedback_prompt message
      // pushed after this one, so a thumbs click can report which query/
      // intent it was actually about.
      feedbackIntent: result.db_intent || result.intent || "",
      // IMPORTANT FIX
      errorDetails: result.error_details || [],
      jobId,
      ...extra
    };
    setMessages((prev) => {
      if (!extra.insertBeforeTrailingMenu) {
        return [...prev, resultMsg];
      }
      let insertAt = prev.length;
      while (insertAt > 0 && ["action_menu", "feedback_prompt"].includes(prev[insertAt - 1].role)) {
        insertAt -= 1;
      }
      if (insertAt === prev.length) {
        return [...prev, resultMsg];
      }
      const next = [...prev];
      next.splice(insertAt, 0, resultMsg);
      return next;
    });
    if (result.result_type !== "guided_input" && result.result_type !== "guided_menu") {
      setIsGuidedFlow(false);
    }
    if (jobId) {
      setTimeout(() => pollForErrors(jobId), 500);
    }
    const shouldShowActionMenu = result.result_type === "error" || isTerminal;
    const isDbQa = result.result_type === "db_qa_result";
    const awaitingSummary = result.result_type === "variance_table" && !result.llm_summary;
    if (extra.insertBeforeTrailingMenu) {
      setTimeout(() => {
        setMessages((prev) => {
          const tail = prev[prev.length - 1];
          if (!tail || tail.role === "action_menu" || tail.role === "feedback_prompt") return prev;
          if (tail.resultType === "ask_previous") return prev;
          const lastUser = [...prev].reverse().find((m) => m.role === "user");
          return [
            ...prev,
            { role: "feedback_prompt", query: lastUser?.text || null, intent: resultMsg.feedbackIntent || null, resultType: resultMsg.resultType || null },
            { role: "action_menu" }
          ];
        });
      }, 800);
    } else if (awaitingSummary) {
      pendingFollowUpRef.current = {
        intent: resultMsg.feedbackIntent || null,
        resultType: resultMsg.resultType || null
      };
    } else if (isTerminal && !jobId) {
      setTimeout(() => {
        setMessages((prev) => {
          const lastUser = [...prev].reverse().find((m) => m.role === "user");
          const feedbackMsg = {
            role: "feedback_prompt",
            query: lastUser?.text || null,
            intent: resultMsg.feedbackIntent || null,
            resultType: resultMsg.resultType || null
          };
          return isDbQa ? [...prev, feedbackMsg] : [...prev, feedbackMsg, { role: "action_menu" }];
        });
      }, 800);
    } else if (shouldShowActionMenu) {
      setTimeout(() => {
        setMessages((prev) => [...prev, { role: "action_menu" }]);
      }, 800);
    }
  };
  const pollForErrors = (jobId) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    let attempts = 0;
    const MAX_ATTEMPTS = 150;
    const tick = async () => {
      attempts++;
      if (attempts > MAX_ATTEMPTS) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
        return;
      }
      try {
        const data = await fetchStatusErrors(jobId, { lang, loginId: _loginId || null });
        if (data.status === "not_found") {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
          return;
        }
        if (data.status === "done") {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
          setMessages(
            (prev) => prev.map((msg) => {
              if (String(msg.jobId) !== String(jobId)) return msg;
              const cleanText = msg.text.replace(/\n*Generating error explanations…/g, "").replace(/\n*Errors Found\s*:\s*\d+/g, "").trimEnd();
              const newErrorDetails = data.error_details || [];
              const errorMessages = newErrorDetails.map((e) => {
                const ti = e?.table_info ?? {};
                const cell = ti.cell_code || e.cellCode || e.cell || "";
                const msg2 = e.explanation || ti.validation_error || e.message || "";
                return cell && msg2 ? `${cell} \u2192 ${msg2}` : msg2;
              }).filter(Boolean);
              const failureText = errorMessages.length ? `

Failure Reason(s):
${errorMessages.map((m) => `\u2022 ${m}`).join("\n")}` : "";
              return {
                ...msg,
                text: cleanText + failureText,
                errorDetails: newErrorDetails
              };
            })
          );
          setTimeout(() => {
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "feedback_prompt") return prev;
              const resultIdx = prev.findIndex((m) => String(m.jobId) === String(jobId));
              const resultMsg = resultIdx >= 0 ? prev[resultIdx] : null;
              const lastUser = [...prev].reverse().find((m) => m.role === "user");
              return [...prev, {
                role: "feedback_prompt",
                query: lastUser?.text || null,
                intent: resultMsg?.feedbackIntent || null,
                resultType: resultMsg?.resultType || null
              }];
            });
          }, 800);
        }
      } catch (err) {
      }
    };
    pollIntervalRef.current = setInterval(tick, 3e3);
  };
  const _beginRequest = () => {
    const controller = new AbortController();
    const requestId = crypto.randomUUID();
    activeRequestRef.current = { controller, requestId };
    return { signal: controller.signal, requestId };
  };
  const _endRequest = (requestId) => {
    if (activeRequestRef.current?.requestId === requestId) {
      activeRequestRef.current = null;
    }
  };
  const handleStop = () => {
    const active = activeRequestRef.current;
    if (!active) return;
    active.controller.abort();
    stopRequest(active.requestId);
    activeRequestRef.current = null;
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setIsLoading(false);
  };
  const submitChatMessage = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    const recentHistory = _getRecentHistory(messages);
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setIsLoading(true);
    const { signal, requestId } = _beginRequest();
    try {
      const result = await sendMessage(
        trimmed,
        sessionId.current,
        _aspSession || null,
        _loginId || null,
        _uid || null,
        _roleId || null,
        recentHistory,
        { signal, requestId, tenantId: _tenantId || null, domain: _domain || null, jwt: jwtRef.current || null, lang }
      );
      _pushResult(result);
    } catch (err) {
      if (err.name === "AbortError") return;
      setIsGuidedFlow(false);
      setMessages((prev) => [
        ...prev,
        { role: "error", text: err.message || t(err.i18nKey || "errorGeneric") }
      ]);
    } finally {
      _endRequest(requestId);
      setIsLoading(false);
    }
  };
  const submitGuidedStep = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setIsLoading(true);
    const { signal, requestId } = _beginRequest();
    try {
      const result = await sendGuidedMessage(
        trimmed,
        sessionId.current,
        _aspSession || null,
        _loginId || null,
        _uid || null,
        _roleId || null,
        { signal, requestId, tenantId: _tenantId || null, domain: _domain || null, jwt: jwtRef.current || null, lang }
      );
      _pushResult(result);
    } catch (err) {
      if (err.name === "AbortError") return;
      setIsGuidedFlow(false);
      setMessages((prev) => [
        ...prev,
        { role: "error", text: err.message || t(err.i18nKey || "errorGeneric") }
      ]);
    } finally {
      _endRequest(requestId);
      setIsLoading(false);
    }
  };
  const handleGuidedAction = async (action) => {
    if (isLoading) return;
    setIsGuidedFlow(true);
    setMessages((prev) => [...prev, { role: "user", text: action }]);
    setIsLoading(true);
    const { signal, requestId } = _beginRequest();
    try {
      const result = await sendGuidedMessage(
        action,
        sessionId.current,
        _aspSession || null,
        _loginId || null,
        _uid || null,
        _roleId || null,
        { signal, requestId, tenantId: _tenantId || null, domain: _domain || null, jwt: jwtRef.current || null, lang }
      );
      _pushResult(result);
    } catch (err) {
      if (err.name === "AbortError") return;
      setIsGuidedFlow(false);
      setMessages((prev) => [...prev, { role: "error", text: err.message || t(err.i18nKey || "errorGeneric") }]);
    } finally {
      _endRequest(requestId);
      setIsLoading(false);
    }
  };
  const handleCompareInstances = async (idxA, idxB) => {
    if (isLoading) return;
    setMessages((prev) => [...prev, { role: "user", text: t("comparativeAnalysis.compareInstances") }]);
    setIsLoading(true);
    const { signal, requestId } = _beginRequest();
    try {
      const result = await compareInstances(sessionId.current, idxA, idxB, { signal, requestId, tenantId: _tenantId || null, domain: _domain || null, jwt: jwtRef.current || null, lang });
      _pushResult(result);
    } catch (err) {
      if (err.name === "AbortError") return;
      setIsGuidedFlow(false);
      setMessages((prev) => [
        ...prev,
        { role: "error", text: err.message || t(err.i18nKey || "errorComparison") }
      ]);
    } finally {
      _endRequest(requestId);
      setIsLoading(false);
    }
  };
  const handleExplainCategory = async (category, errorFilePath, formId = null, reportName = null, offset = 0) => {
    if (isLoading) return;
    setIsLoading(true);
    const { signal, requestId } = _beginRequest();
    try {
      const result = await explainErrorCategory(errorFilePath, category, formId, reportName, { signal, requestId, offset, tenantId: _tenantId || null, domain: _domain || null, jwt: jwtRef.current || null, lang });
      _pushResult(result, {
        batchCategory: category,
        batchErrorFilePath: errorFilePath,
        batchFormId: formId,
        batchReportName: reportName,
        // See _pushResult: an explain-category result belongs directly under
        // the failed-report card the user is still reading, not after the
        // "what would you like to do next?" menu that auto-appeared while
        // they were choosing which category to explain.
        insertBeforeTrailingMenu: true
      });
    } catch (err) {
      if (err.name === "AbortError") return;
      setMessages((prev) => [
        ...prev,
        { role: "error", text: err.message || t(err.i18nKey || "errorExplanations") }
      ]);
    } finally {
      _endRequest(requestId);
      setIsLoading(false);
    }
  };
  const handleSummaryLoaded = (idx, text) => {
    const followUp = pendingFollowUpRef.current;
    pendingFollowUpRef.current = null;
    setMessages((prev) => {
      const updated = prev.map((m, i) => i === idx ? { ...m, llmSummary: text || m.llmSummary || "", noAutoSummary: true } : m);
      if (!followUp) return updated;
      if (updated[updated.length - 1]?.role === "feedback_prompt" || updated[updated.length - 1]?.role === "action_menu") return updated;
      const lastUser = [...updated].reverse().find((m) => m.role === "user");
      return [
        ...updated,
        {
          role: "feedback_prompt",
          query: lastUser?.text || null,
          intent: followUp.intent,
          resultType: followUp.resultType
        },
        { role: "action_menu" }
      ];
    });
  };
  const handleFeedback = (response, context = {}) => {
    sendFeedback(response === "yes" ? "up" : "down", {
      query: context.query ?? null,
      intent: context.intent ?? null,
      resultType: context.resultType ?? null,
      sessionId: sessionId.current
    });
    if (response === "yes") {
      setMessages((prev) => [...prev, { role: "feedback_positive" }]);
    } else {
      setMessages((prev) => [...prev, { role: "feedback_negative" }]);
    }
  };
  const handleSuggestion = (text) => {
    if (isGuidedFlow) {
      submitGuidedStep(text);
    } else {
      submitChatMessage(text);
    }
  };
  const handleTranscript = (transcript) => {
    setInputText(transcript);
    inputRef.current?.focus();
  };
  const handleSubmit = async (e) => {
    e?.preventDefault();
    const text = inputText.trim();
    if (!text || isLoading) return;
    setInputText("");
    if (isGuidedFlow) {
      await submitGuidedStep(text);
    } else {
      await submitChatMessage(text);
    }
  };
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };
  const t = makeT(lang);
  const placeholder = voiceState === "recording" ? t("voice.speakNow") : voiceState === "processing" ? t("voice.transcribing") : t(isGuidedFlow ? "inputPlaceholderGuided" : "inputPlaceholder");
  return (
    // lang is read by every card below via useT(). dir drives RTL layout for
    // Arabic — a pure CSS/markup concern, so no model is involved in it.
    /* @__PURE__ */ h(LanguageContext.Provider, { value: lang }, /* @__PURE__ */ h("div", { className: "app-shell", dir: isRtl(lang) ? "rtl" : "ltr" }, /* @__PURE__ */ h("main", { className: "chat-area" }, /* @__PURE__ */ h(
      ChatWindow,
      {
        messages,
        isLoading,
        onSuggestion: handleSuggestion,
        onGuidedAction: handleGuidedAction,
        onCompare: handleCompareInstances,
        onFeedback: handleFeedback,
        onExplainCategory: handleExplainCategory,
        onSummaryLoaded: handleSummaryLoaded,
        allowedActions,
        lang,
        onLanguageChange: setLang,
        loginId: _loginId || null,
        tenantId: _tenantId || null,
        domain: _domain || null,
        jwtRef
      }
    )), /* @__PURE__ */ h("footer", { className: "input-bar" }, isGuidedFlow && /* @__PURE__ */ h("div", { className: "guided-mode-indicator" }, t("guidedModeIndicator")), /* @__PURE__ */ h("form", { className: "input-form", onSubmit: handleSubmit }, /* @__PURE__ */ h(
      VoiceInput,
      {
        onTranscript: handleTranscript,
        onStateChange: setVoiceState,
        disabled: isLoading
      }
    ), /* @__PURE__ */ h(
      "textarea",
      {
        ref: inputRef,
        className: "text-input",
        value: inputText,
        onChange: (e) => setInputText(e.target.value),
        onKeyDown: handleKeyDown,
        placeholder,
        rows: 1,
        disabled: isLoading
      }
    ), /* @__PURE__ */ h(
      "button",
      {
        type: "button",
        className: "clear-chat-btn",
        onClick: handleClearChat,
        title: t("clearChat"),
        "aria-label": t("clearChat")
      },
      /* @__PURE__ */ h(TrashIcon, null)
    ), isLoading ? /* @__PURE__ */ h(
      "button",
      {
        type: "button",
        className: "send-btn stop-btn",
        onClick: handleStop,
        "aria-label": t("stopGenerating"),
        title: t("stopGenerating")
      },
      /* @__PURE__ */ h(StopIcon, null)
    ) : /* @__PURE__ */ h(
      "button",
      {
        type: "submit",
        className: "send-btn",
        disabled: !inputText.trim(),
        "aria-label": t("sendMessage")
      },
      /* @__PURE__ */ h(SendIcon, null)
    )), /* @__PURE__ */ h("p", { className: "ai-disclaimer" }, "AI-generated responses may be inaccurate \u2014 please verify important details against the application before acting on them."))))
  );
}
function SendIcon() {
  return /* @__PURE__ */ h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ h("line", { x1: "22", y1: "2", x2: "11", y2: "13" }), /* @__PURE__ */ h("polygon", { points: "22 2 15 22 11 13 2 9 22 2" }));
}
function StopIcon() {
  return /* @__PURE__ */ h("svg", { viewBox: "0 0 24 24", fill: "currentColor" }, /* @__PURE__ */ h("rect", { x: "6", y: "6", width: "12", height: "12", rx: "2" }));
}
function TrashIcon() {
  return /* @__PURE__ */ h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round", width: "14", height: "14" }, /* @__PURE__ */ h("polyline", { points: "3 6 5 6 21 6" }), /* @__PURE__ */ h("path", { d: "M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" }), /* @__PURE__ */ h("path", { d: "M10 11v6M14 11v6" }), /* @__PURE__ */ h("path", { d: "M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" }));
}
export {
  App as default
};
