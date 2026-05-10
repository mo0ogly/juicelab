/*
 * juicelab-overlay - Scoring service
 * Computes deductive score based on consumed hints with floor 50.
 * SPDX-License-Identifier: MIT
 */

import { Injectable } from '@angular/core'

import {
  HINT_COST_BY_LEVEL,
  type HintLevel,
  SCORE_FLOOR,
  SCORE_INITIAL,
} from '../models/juicelab.types'

@Injectable({ providedIn: 'root' })
export class JuicelabScoringService {
  /** Compute score after consuming the given hint levels. */
  scoreFromConsumedHints(consumed: HintLevel[]): number {
    const totalCost = consumed.reduce((sum, lvl) => sum + HINT_COST_BY_LEVEL[lvl], 0)
    return Math.max(SCORE_FLOOR, SCORE_INITIAL - totalCost)
  }

  /** Cost of revealing the next hint at the given level. */
  costOf(level: HintLevel): number {
    return HINT_COST_BY_LEVEL[level]
  }

  /** Approximate quiz scoring against expected_keywords for free_text questions. */
  scoreQuizAnswer(
    answer: string,
    expectedKeywords: string[] | undefined,
  ): number {
    if (!expectedKeywords || expectedKeywords.length === 0) return 0
    const lower = answer.toLowerCase()
    const matches = expectedKeywords.filter(k => lower.includes(k.toLowerCase())).length
    return Math.round((matches / expectedKeywords.length) * 100)
  }
}
