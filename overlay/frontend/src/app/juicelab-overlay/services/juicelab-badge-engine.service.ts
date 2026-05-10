/*
 * juicelab-overlay - Badge engine
 * Evaluates badge rules against the local state, awards new ones.
 * SPDX-License-Identifier: MIT
 */

import { Injectable, inject } from '@angular/core'

import { type Badge, type LocalState } from '../models/juicelab.types'
import { JuicelabStateService } from './juicelab-state.service'

const DJ1_KEYS = [
  'scoreBoardChallenge',
  'privacyPolicyChallenge',
  'directoryListingChallenge',
  'exposedCredentialsChallenge',
  'passwordHashLeakChallenge',
]
const DJ2_KEYS = [
  'loginAdminChallenge',
  'adminSectionChallenge',
  'basketAccessChallenge',
  'feedbackChallenge',
]
const DJ3_KEYS = [
  'localXssChallenge',
  'reflectedXssChallenge',
  'xssBonusChallenge',
  'bullyChatbotChallenge',
]
const ALL_KEYS = [...DJ1_KEYS, ...DJ2_KEYS, ...DJ3_KEYS]

export const BADGES: Badge[] = [
  {
    key: 'recon_master',
    label_fr: 'Recon Master',
    label_en: 'Recon Master',
    description_fr: 'DJ1 entierement resolu sans aucun indice consomme.',
    description_en: 'DJ1 fully solved without consuming any hint.',
    icon: 'visibility',
  },
  {
    key: 'perseverant',
    label_fr: 'Perseverant',
    label_en: 'Persistent',
    description_fr: 'TD entier resolu malgre la consommation maximale d indices.',
    description_en: 'Whole TD solved despite consuming the maximum hints.',
    icon: 'fitness_center',
  },
  {
    key: 'metacognitif',
    label_fr: 'Meta-cognitif',
    label_en: 'Reflective',
    description_fr: 'Tous les journaux after_solve avec qualite > 50 mots.',
    description_en: 'All after_solve journals exceed 50 words.',
    icon: 'psychology',
  },
  {
    key: 'apex',
    label_fr: 'Apex Predator',
    label_en: 'Apex Predator',
    description_fr: 'TD complet sans aucun indice consomme.',
    description_en: 'Whole TD solved without consuming a single hint.',
    icon: 'military_tech',
  },
]

@Injectable({ providedIn: 'root' })
export class JuicelabBadgeEngineService {
  private readonly stateSvc = inject(JuicelabStateService)

  /** Re-evaluate all badges against the current state and award new ones. */
  reevaluateAll(): string[] {
    const state = this.stateSvc.state()
    const newlyAwarded: string[] = []

    for (const badge of BADGES) {
      if (state.badges_earned.includes(badge.key)) continue
      if (this.matches(badge.key, state)) {
        this.stateSvc.awardBadge(badge.key)
        newlyAwarded.push(badge.key)
      }
    }
    return newlyAwarded
  }

  private matches(badgeKey: string, state: LocalState): boolean {
    switch (badgeKey) {
      case 'recon_master':
        return this.allSolved(state, DJ1_KEYS) && this.totalHints(state, DJ1_KEYS) === 0
      case 'apex':
        return this.allSolved(state, ALL_KEYS) && this.totalHints(state, ALL_KEYS) === 0
      case 'perseverant':
        return this.allSolved(state, ALL_KEYS) && this.totalHints(state, ALL_KEYS) > 30
      case 'metacognitif':
        return this.allSolved(state, ALL_KEYS) && ALL_KEYS.every(k => {
          const j = state.challenges[k]?.journal.after_solve ?? ''
          return j.split(/\s+/).filter(Boolean).length > 50
        })
      default:
        return false
    }
  }

  private allSolved(state: LocalState, keys: string[]): boolean {
    return keys.every(k => state.challenges[k]?.solved_at)
  }

  private totalHints(state: LocalState, keys: string[]): number {
    return keys.reduce((sum, k) => sum + (state.challenges[k]?.hints_consumed.length ?? 0), 0)
  }
}
