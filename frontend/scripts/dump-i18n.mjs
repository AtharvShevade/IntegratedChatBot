// Prints the static-text dictionary as JSON on stdout.
//
// Exists so backend/tests/test_i18n_static_strings.py can assert the
// invariants that span the JS/Python boundary -- above all that ACTIONS is
// keyed by exactly the English tokens in backend/guided.py's GUIDED_ACTIONS.
// Reading the real module beats regex-parsing the source.
//
//   node scripts/dump-i18n.mjs
import {
  STRINGS, ACTIONS, ACTION_DESCRIPTIONS, OPTION_LABELS, UI,
  LANGUAGES, RTL_LANGUAGES,
} from '../src/i18n.js'

process.stdout.write(JSON.stringify({
  STRINGS, ACTIONS, ACTION_DESCRIPTIONS, OPTION_LABELS, UI,
  LANGUAGES, RTL: [...RTL_LANGUAGES],
}))
