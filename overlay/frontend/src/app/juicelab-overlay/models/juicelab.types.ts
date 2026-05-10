/*
 * juicelab-overlay - Type definitions
 * SPDX-License-Identifier: MIT
 */

export type Lang = 'fr' | 'en'

export type HintLevel = 'N1' | 'N2' | 'N3' | 'N4' | 'N5'

/** Hint as loaded from hints/{key}.yaml. */
export interface Hint {
  cost_pct: number
  text_fr: string
  text_en: string
  pedagogical_intent: string
}

/** Hints pack for one challenge. */
export interface HintsPack {
  challenge_key: string
  schema_version: string
  hints: Record<HintLevel, Hint>
}

/** Single quiz question. */
export interface QuizQuestion {
  type: 'free_text' | 'multiple_choice'
  question_fr: string
  question_en: string
  expected_keywords_fr?: string[]
  expected_keywords_en?: string[]
  rubric_fr?: string
  rubric_en?: string
  options_fr?: string[]
  options_en?: string[]
  correct?: number
  explanation_fr?: string
  explanation_en?: string
}

/** Quiz pack for one challenge. */
export interface QuizPack {
  challenge_key: string
  quiz: {
    Q1: QuizQuestion
    Q2: QuizQuestion
    Q3: QuizQuestion
  }
}

/** Single briefing concept (security topic explained). */
export interface BriefingConcept {
  title_fr: string
  title_en: string
  body_fr: string
  body_en: string
}

/** Pre-challenge briefing pack — replaces the legacy "before" journal prompt
 *  with a structured mission + concepts exposes block. Loaded as a public
 *  static asset (no solutions inside). */
export interface BriefingPack {
  challenge_key: string
  schema_version: string
  mission_fr: string
  mission_en: string
  concepts: BriefingConcept[]
}

/** Journal prompts pack for one challenge. */
export interface JournalPack {
  challenge_key: string
  journal_prompts: {
    before_solve_fr: string
    before_solve_en: string
    after_solve_fr: string
    after_solve_en: string
  }
}

/** Local persisted state for a single challenge attempt. */
export interface ChallengeState {
  hints_consumed: HintLevel[]
  score_net: number
  journal: {
    before_solve: string
    after_solve: string
  }
  quiz: {
    Q1: string
    Q2: number | null
    Q3: string
    score: number
  }
  time_spent_s: number
  solved_at: string | null
  started_at: string
  flag_captured: boolean
  flag_captured_at: string | null
}

/** Top-level local state stored in LocalStorage. */
export interface LocalState {
  schema_version: 1
  student: {
    token: string
    cohort: string
    language: Lang
  }
  challenges: Record<string, ChallengeState>
  badges_earned: string[]
}

/** Plugin runtime config served at /assets/juicelab/config.json. */
export interface JuicelabConfig {
  dashboard_url: string
  cohort_id: string
  instance_label: string
  default_language: Lang
}

/** Quiz question stripped of expected answers (phase B). */
export interface QuizQuestionPublic {
  type: 'free_text' | 'multiple_choice'
  question_fr?: string
  question_en?: string
  options_fr?: string[]
  options_en?: string[]
}

/** Quiz pack stripped of answers (phase B). */
export interface QuizPackPublic {
  challenge_key: string
  quiz: {
    Q1: QuizQuestionPublic
    Q2: QuizQuestionPublic
    Q3: QuizQuestionPublic
  }
}

/** Single hint response from /api/juicelab/hint (phase B). */
export interface HintResponse {
  challenge_key: string
  level: HintLevel
  cost_pct: number
  text_fr: string
  text_en: string
  consumed_levels: HintLevel[]
}

/** Quiz scoring response from /api/juicelab/quiz/score (phase B). */
export interface QuizScoreResponse {
  score: number
  by_question: { Q1: number, Q2: number, Q3: number }
}

/** Walkthrough response from /api/juicelab/walkthrough (phase B). */
export interface WalkthroughResponse {
  challenge_key: string
  language: Lang
  markdown: string
}

/** Badge definition. */
export interface Badge {
  key: string
  label_fr: string
  label_en: string
  description_fr: string
  description_en: string
  icon: string
}

/** Outbound event sent to the dashboard cloud. */
export interface SyncEvent {
  student_token: string
  cohort_id: string
  event_type:
    | 'hint_revealed'
    | 'challenge_solved'
    | 'journal_filled'
    | 'quiz_completed'
    | 'badge_earned'
    | 'session_start'
    | 'session_end'
  challenge_key?: string
  data: Record<string, unknown>
  client_timestamp: string
}

/** Selection of TD challenges (subset of selected_challenges.yml). */
export interface SelectedChallenge {
  key: string
  name_official: string
  demi_journee: 1 | 2 | 3
  position: number
  difficulty: number
  category: string
}

export const HINT_COST_BY_LEVEL: Record<HintLevel, number> = {
  N1: 5,
  N2: 10,
  N3: 20,
  N4: 35,
  N5: 50,
}

export const SCORE_FLOOR = 50
export const SCORE_INITIAL = 100
