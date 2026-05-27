// MainMap interaction-state reducer (post-A-1 expanded scope).
//
// Owns ALL "which panel is open?" state — right-side slide-in panels
// (AdongPanel / TransactionPanel / KernelScorePanel are mutually exclusive),
// the bottom-left CriteriaPanel collapse state, and the ephemeral
// first-time coach-mark.
//
// State machine diagram (post-design-polish-v2 R-1):
//
//   ┌─────────────┐  open_dong   ┌──────────────────┐
//   │ idle (none) │ ───────────→ │ AdongPanel (right)│
//   └─────────────┘              └──────────────────┘
//        ▲ ▲                            │
//        │ │ close_all_right            │ open_jibun / open_kernel
//        │ └────────────────────────────┘
//        │                              │
//   open_jibun                          ▼
//        │                       ┌──────────────────┐
//        ▼                       │ TxPanel (right)  │
//   ┌──────────────────┐         └──────────────────┘
//   │ KernelPanel(rt)  │
//   └──────────────────┘
//
// Independent: criteriaOpen (bottom-left, toggles), coachVisible (4s timer
// or first user interaction).
//
// criteriaOpen auto-collapses when ANY right-side panel opens (saves canvas
// for the slide-in panel).
//
// IMPORTANT INVARIANT (failure-mode mitigation per /plan-eng-review):
// every `open_*` action MUST set the OTHER two selectedSlug/selectedJibun/
// kernelPoint fields to null. Adding a new "open" action without doing
// this would silently break mutual exclusion. The unit-test-equivalent
// here is a manual smoke through every action — no automated tests in
// this project (`.gstack/no-test-bootstrap`).

import type { LatLng } from '@/hooks/useKernelScore';
import type { Weights } from '@/types/api';
import { DEFAULT_WEIGHTS } from '@/types/api';

export interface PanelState {
  // Right-side slide-in panels (mutually exclusive).
  selectedSlug: string | null;
  selectedJibun: string | null;
  kernelPoint: LatLng | null;

  // KernelScorePanel-internal state (coupled to kernelPoint lifetime).
  kernelWeights: Weights;
  kernelSchool: string;

  // Bottom-left CriteriaPanel.
  criteriaOpen: boolean;

  // Ephemeral first-time UX (D-10).
  coachVisible: boolean;
}

export const INITIAL_PANEL_STATE: PanelState = {
  selectedSlug: null,
  selectedJibun: null,
  kernelPoint: null,
  kernelWeights: DEFAULT_WEIGHTS,
  kernelSchool: '',
  criteriaOpen: false,
  coachVisible: true,
};

export type PanelAction =
  | { type: 'toggle_criteria' }
  | { type: 'open_dong'; slug: string }
  | { type: 'open_jibun'; key: string }
  | { type: 'open_kernel'; point: LatLng; resetWeightsTo: Weights }
  | { type: 'close_all_right' }
  | { type: 'set_kernel_weights'; weights: Weights }
  | { type: 'set_kernel_school'; school: string }
  | { type: 'dismiss_coach' };

/** Empty all three slide-in panel selections. Used by every open_* action
 *  and by close_all_right. Centralizes the mutual-exclusion invariant. */
function clearRightSelections(): Pick<
  PanelState,
  'selectedSlug' | 'selectedJibun' | 'kernelPoint'
> {
  return {
    selectedSlug: null,
    selectedJibun: null,
    kernelPoint: null,
  };
}

export function panelReducer(state: PanelState, action: PanelAction): PanelState {
  switch (action.type) {
    case 'toggle_criteria':
      return {
        ...state,
        criteriaOpen: !state.criteriaOpen,
        // Any user interaction dismisses the coach-mark.
        coachVisible: false,
      };

    case 'open_dong':
      return {
        ...state,
        ...clearRightSelections(),
        selectedSlug: action.slug,
        criteriaOpen: false,
        coachVisible: false,
      };

    case 'open_jibun':
      return {
        ...state,
        ...clearRightSelections(),
        selectedJibun: action.key,
        criteriaOpen: false,
        coachVisible: false,
      };

    case 'open_kernel':
      return {
        ...state,
        ...clearRightSelections(),
        kernelPoint: action.point,
        kernelWeights: action.resetWeightsTo,
        kernelSchool: '',
        criteriaOpen: false,
        coachVisible: false,
      };

    case 'close_all_right':
      return {
        ...state,
        ...clearRightSelections(),
      };

    case 'set_kernel_weights':
      return { ...state, kernelWeights: action.weights };

    case 'set_kernel_school':
      return { ...state, kernelSchool: action.school };

    case 'dismiss_coach':
      return { ...state, coachVisible: false };

    default:
      return state;
  }
}
