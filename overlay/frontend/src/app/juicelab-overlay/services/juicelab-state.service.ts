/*
 * juicelab-overlay - State service
 * Persists per-student state in LocalStorage with schema versioning.
 * SPDX-License-Identifier: MIT
 */

import { Injectable, signal } from '@angular/core'

import {
  type ChallengeState,
  type HintLevel,
  type Lang,
  type LocalState,
  SCORE_INITIAL,
} from '../models/juicelab.types'

const STORAGE_KEY = 'juicelab_state_v1'

@Injectable({ providedIn: 'root' })
export class JuicelabStateService {
  /** Reactive snapshot of the current state. UI components subscribe via toObservable or read sync. */
  readonly state = signal<LocalState>(this.load())

  /** Initialize state for a fresh student session. Generates a token if absent. */
  ensureStudent(cohort: string, language: Lang): void {
    const current = this.state()
    if (current.student.token) return
    const token = crypto.randomUUID()
    this.update({
      ...current,
      student: { token, cohort, language },
    })
  }

  /** Persist a language choice on the current student record. */
  setLanguage(language: Lang): void {
    const current = this.state()
    if (current.student.language === language) return
    this.update({
      ...current,
      student: { ...current.student, language },
    })
  }


  /** Get or create the state slot for a challenge. */
  getOrInitChallenge(challengeKey: string): ChallengeState {
    const current = this.state()
    const existing = current.challenges[challengeKey]
    if (existing) return existing

    const fresh: ChallengeState = {
      hints_consumed: [],
      score_net: SCORE_INITIAL,
      journal: { before_solve: '', after_solve: '' },
      quiz: { Q1: '', Q2: null, Q3: '', score: 0 },
      time_spent_s: 0,
      solved_at: null,
      started_at: new Date().toISOString(),
      flag_captured: false,
      flag_captured_at: null,
    }
    this.update({
      ...current,
      challenges: { ...current.challenges, [challengeKey]: fresh },
    })
    return fresh
  }

  /** Mark a hint as consumed for a given challenge. Idempotent. */
  consumeHint(challengeKey: string, level: HintLevel, newScore: number): void {
    const current = this.state()
    const challenge = this.getOrInitChallenge(challengeKey)
    if (challenge.hints_consumed.includes(level)) return
    const updated: ChallengeState = {
      ...challenge,
      hints_consumed: [...challenge.hints_consumed, level],
      score_net: newScore,
    }
    this.update({
      ...current,
      challenges: { ...current.challenges, [challengeKey]: updated },
    })
  }

  /** Save journal entry. Phase = 'before' or 'after'. */
  saveJournal(challengeKey: string, phase: 'before' | 'after', text: string): void {
    const current = this.state()
    const challenge = this.getOrInitChallenge(challengeKey)
    const updated: ChallengeState = {
      ...challenge,
      journal: {
        ...challenge.journal,
        [phase === 'before' ? 'before_solve' : 'after_solve']: text,
      },
    }
    this.update({
      ...current,
      challenges: { ...current.challenges, [challengeKey]: updated },
    })
  }

  /** Save quiz answers and resulting score. */
  saveQuiz(
    challengeKey: string,
    answers: { Q1: string; Q2: number | null; Q3: string },
    quizScore: number,
  ): void {
    const current = this.state()
    const challenge = this.getOrInitChallenge(challengeKey)
    const updated: ChallengeState = {
      ...challenge,
      quiz: { ...answers, score: quizScore },
    }
    this.update({
      ...current,
      challenges: { ...current.challenges, [challengeKey]: updated },
    })
  }

  /** Mark a challenge as solved with timestamp. */
  markSolved(challengeKey: string): void {
    const current = this.state()
    const challenge = this.getOrInitChallenge(challengeKey)
    if (challenge.solved_at) return
    const updated: ChallengeState = {
      ...challenge,
      solved_at: new Date().toISOString(),
    }
    this.update({
      ...current,
      challenges: { ...current.challenges, [challengeKey]: updated },
    })
  }

  /** Mark the CTF flag as captured for this challenge. Idempotent — keeps
   *  the original timestamp on a second call so the trophy date is stable. */
  markFlagCaptured(challengeKey: string): void {
    const current = this.state()
    const challenge = this.getOrInitChallenge(challengeKey)
    if (challenge.flag_captured) return
    const updated: ChallengeState = {
      ...challenge,
      flag_captured: true,
      flag_captured_at: new Date().toISOString(),
    }
    this.update({
      ...current,
      challenges: { ...current.challenges, [challengeKey]: updated },
    })
  }

  /** Award a badge. Idempotent. */
  awardBadge(badgeKey: string): void {
    const current = this.state()
    if (current.badges_earned.includes(badgeKey)) return
    this.update({ ...current, badges_earned: [...current.badges_earned, badgeKey] })
  }

  /** Reset all local state. */
  reset(): void {
    localStorage.removeItem(STORAGE_KEY)
    this.state.set(this.empty())
  }

  private update(next: LocalState): void {
    this.state.set(next)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  }

  private load(): LocalState {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return this.empty()
    try {
      const parsed = JSON.parse(raw) as LocalState
      if (parsed.schema_version === 1) return parsed
    } catch {
      /* fall through to empty */
    }
    return this.empty()
  }

  private empty(): LocalState {
    return {
      schema_version: 1,
      student: { token: '', cohort: '', language: 'fr' },
      challenges: {},
      badges_earned: [],
    }
  }
}
