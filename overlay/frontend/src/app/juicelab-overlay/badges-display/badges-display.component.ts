/*
 * juicelab-overlay - Badges display
 * Tiered medals with per-badge progress hint and theme-safe colors.
 * SPDX-License-Identifier: MIT
 */

import { CommonModule } from '@angular/common'
import { Component, computed, inject } from '@angular/core'
import { MatCardModule } from '@angular/material/card'
import { MatIconModule } from '@angular/material/icon'
import { MatTooltipModule } from '@angular/material/tooltip'

import { type Badge, type LocalState } from '../models/juicelab.types'
import { BADGES, JuicelabBadgeEngineService } from '../services/juicelab-badge-engine.service'
import { JuicelabStateService } from '../services/juicelab-state.service'

type Tier = 'recon' | 'grit' | 'meta' | 'apex'

interface DecoratedBadge extends Badge {
  earned: boolean
  tier: Tier
  progressFr: string
  progressEn: string
}

const DJ1_KEYS = [
  'scoreBoardChallenge',
  'privacyPolicyChallenge',
  'directoryListingChallenge',
  'exposedCredentialsChallenge',
  'passwordHashLeakChallenge',
]
const ALL_KEYS = [
  ...DJ1_KEYS,
  'loginAdminChallenge',
  'adminSectionChallenge',
  'basketAccessChallenge',
  'feedbackChallenge',
  'localXssChallenge',
  'reflectedXssChallenge',
  'xssBonusChallenge',
  'bullyChatbotChallenge',
]

@Component({
  selector: 'juicelab-badges-display',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatTooltipModule],
  template: `
    <mat-card class="badges-display">
      <mat-card-title>
        <mat-icon>workspace_premium</mat-icon>
        Badges
      </mat-card-title>
      <mat-card-content>
        <div class="grid">
          <div
            *ngFor="let badge of decorated()"
            class="badge"
            [class.earned]="badge.earned"
            [attr.data-tier]="badge.tier"
            [matTooltip]="(language() === 'fr' ? badge.description_fr : badge.description_en)"
            matTooltipPosition="above"
          >
            <div class="medal">
              <div class="medal-ring"></div>
              <mat-icon class="icon">{{ badge.icon }}</mat-icon>
              <mat-icon class="lock" *ngIf="!badge.earned">lock</mat-icon>
              <mat-icon class="tick" *ngIf="badge.earned">verified</mat-icon>
            </div>
            <div class="meta">
              <div class="label">{{ language() === 'fr' ? badge.label_fr : badge.label_en }}</div>
              <div class="desc">{{ language() === 'fr' ? badge.description_fr : badge.description_en }}</div>
              <div class="progress" *ngIf="!badge.earned">
                <span class="chip">{{ language() === 'fr' ? badge.progressFr : badge.progressEn }}</span>
              </div>
              <div class="progress" *ngIf="badge.earned">
                <span class="chip earned-chip">
                  <mat-icon class="chip-icon">check_circle</mat-icon>
                  {{ language() === 'fr' ? 'Acquis' : 'Earned' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </mat-card-content>
    </mat-card>
  `,
  styles: [`
    :host { display: block; color: inherit; }
    .badges-display { max-width: 720px; margin: 16px 0; color: inherit; }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 14px;
    }
    @media (max-width: 540px) { .grid { grid-template-columns: 1fr; } }

    .badge {
      position: relative;
      display: flex;
      gap: 14px;
      padding: 14px 16px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.035);
      border: 1px solid rgba(255, 255, 255, 0.08);
      transition: transform 200ms ease, border-color 200ms ease, background 200ms ease, box-shadow 200ms ease;
      overflow: hidden;
    }
    .badge::before {
      content: '';
      position: absolute;
      inset: 0;
      background: radial-gradient(circle at 12% 0%, var(--tier-color, transparent) 0%, transparent 35%);
      opacity: 0;
      transition: opacity 220ms ease;
      pointer-events: none;
    }
    .badge:hover {
      transform: translateY(-2px);
      border-color: rgba(255, 255, 255, 0.18);
    }
    .badge:hover::before { opacity: 0.18; }

    .badge.earned {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.02));
      border-color: var(--tier-color);
      box-shadow:
        0 0 0 1px var(--tier-color) inset,
        0 10px 30px -12px var(--tier-color);
    }
    .badge.earned::before { opacity: 0.22; }

    /* Tier accent palette - bright on dark, also OK on light */
    .badge[data-tier="recon"] { --tier-color: #38bdf8; }
    .badge[data-tier="grit"]  { --tier-color: #fb923c; }
    .badge[data-tier="meta"]  { --tier-color: #c084fc; }
    .badge[data-tier="apex"]  { --tier-color: #fbbf24; }

    .medal {
      position: relative;
      width: 60px;
      height: 60px;
      flex: 0 0 60px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: rgba(0, 0, 0, 0.18);
      border: 2px solid rgba(255, 255, 255, 0.10);
      transition: border-color 200ms ease, background 200ms ease, transform 240ms ease;
    }
    .badge.earned .medal {
      background:
        radial-gradient(circle at 30% 30%, color-mix(in srgb, var(--tier-color) 70%, transparent), color-mix(in srgb, var(--tier-color) 25%, transparent) 60%, rgba(0, 0, 0, 0.25) 100%);
      border-color: var(--tier-color);
      transform: rotate(-3deg);
    }
    .medal-ring {
      position: absolute;
      inset: -3px;
      border-radius: 50%;
      border: 1px dashed transparent;
      pointer-events: none;
    }
    .badge.earned .medal-ring {
      border-color: color-mix(in srgb, var(--tier-color) 70%, transparent);
      animation: spin 14s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .icon {
      font-size: 28px;
      width: 28px;
      height: 28px;
      opacity: 0.55;
      transition: opacity 200ms ease;
    }
    .badge.earned .icon {
      opacity: 1;
      filter: drop-shadow(0 0 6px color-mix(in srgb, var(--tier-color) 60%, transparent));
    }

    .lock, .tick {
      position: absolute;
      bottom: -2px;
      right: -2px;
      font-size: 16px;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      padding: 1px;
    }
    .lock {
      background: rgba(0, 0, 0, 0.78);
      color: rgba(255, 255, 255, 0.78);
      border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .tick {
      background: var(--tier-color);
      color: #0b0f17;
      border: 1px solid rgba(0, 0, 0, 0.45);
    }

    .meta { min-width: 0; flex: 1; }
    .label {
      font-weight: 700;
      letter-spacing: 0.3px;
      margin-bottom: 4px;
      font-size: 14px;
    }
    .desc {
      font-size: 12px;
      line-height: 1.45;
      opacity: 0.7;
      margin-bottom: 8px;
    }
    .progress { display: flex; }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      padding: 3px 9px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.08);
      color: inherit;
      font-weight: 600;
      letter-spacing: 0.3px;
      border: 1px solid rgba(255, 255, 255, 0.12);
    }
    .badge[data-tier="recon"] .chip { border-color: color-mix(in srgb, var(--tier-color) 50%, transparent); }
    .badge[data-tier="grit"]  .chip { border-color: color-mix(in srgb, var(--tier-color) 50%, transparent); }
    .badge[data-tier="meta"]  .chip { border-color: color-mix(in srgb, var(--tier-color) 50%, transparent); }
    .badge[data-tier="apex"]  .chip { border-color: color-mix(in srgb, var(--tier-color) 50%, transparent); }
    .earned-chip {
      background: var(--tier-color);
      color: #0b0f17;
      border-color: var(--tier-color);
    }
    .chip-icon {
      font-size: 12px;
      width: 12px;
      height: 12px;
    }
  `],
})
export class BadgesDisplayComponent {
  private readonly stateSvc = inject(JuicelabStateService)
  private readonly engine = inject(JuicelabBadgeEngineService)

  readonly language = computed(() => this.stateSvc.state().student.language)

  readonly decorated = computed<DecoratedBadge[]>(() => {
    const state = this.stateSvc.state()
    const earned = new Set(state.badges_earned)
    return BADGES.map(b => ({
      ...b,
      earned: earned.has(b.key),
      tier: this.tierOf(b.key),
      progressFr: this.progressFr(b.key, state),
      progressEn: this.progressEn(b.key, state),
    }))
  })

  ngOnInit(): void {
    this.engine.reevaluateAll()
  }

  private tierOf(key: string): Tier {
    switch (key) {
      case 'recon_master': return 'recon'
      case 'perseverant': return 'grit'
      case 'metacognitif': return 'meta'
      case 'apex': return 'apex'
      default: return 'recon'
    }
  }

  private solvedCount(state: LocalState, keys: string[]): number {
    return keys.reduce((n, k) => n + (state.challenges[k]?.solved_at ? 1 : 0), 0)
  }

  private hintCount(state: LocalState, keys: string[]): number {
    return keys.reduce((n, k) => n + (state.challenges[k]?.hints_consumed.length ?? 0), 0)
  }

  private journalReadyCount(state: LocalState, keys: string[]): number {
    return keys.reduce((n, k) => {
      const text = state.challenges[k]?.journal.after_solve ?? ''
      return n + (text.split(/\s+/).filter(Boolean).length > 50 ? 1 : 0)
    }, 0)
  }

  private progressFr(key: string, state: LocalState): string {
    if (key === 'recon_master') {
      const solved = this.solvedCount(state, DJ1_KEYS)
      const hints = this.hintCount(state, DJ1_KEYS)
      return `DJ1 ${solved}/5 - ${hints} indices`
    }
    if (key === 'apex') {
      const solved = this.solvedCount(state, ALL_KEYS)
      const hints = this.hintCount(state, ALL_KEYS)
      return `${solved}/13 - ${hints} indices`
    }
    if (key === 'perseverant') {
      const solved = this.solvedCount(state, ALL_KEYS)
      const hints = this.hintCount(state, ALL_KEYS)
      return `${solved}/13 - ${hints} indices (>30)`
    }
    if (key === 'metacognitif') {
      const ready = this.journalReadyCount(state, ALL_KEYS)
      return `${ready}/13 journaux >50 mots`
    }
    return 'A faire'
  }

  private progressEn(key: string, state: LocalState): string {
    if (key === 'recon_master') {
      const solved = this.solvedCount(state, DJ1_KEYS)
      const hints = this.hintCount(state, DJ1_KEYS)
      return `DJ1 ${solved}/5 - ${hints} hints`
    }
    if (key === 'apex') {
      const solved = this.solvedCount(state, ALL_KEYS)
      const hints = this.hintCount(state, ALL_KEYS)
      return `${solved}/13 - ${hints} hints`
    }
    if (key === 'perseverant') {
      const solved = this.solvedCount(state, ALL_KEYS)
      const hints = this.hintCount(state, ALL_KEYS)
      return `${solved}/13 - ${hints} hints (>30)`
    }
    if (key === 'metacognitif') {
      const ready = this.journalReadyCount(state, ALL_KEYS)
      return `${ready}/13 journals >50 words`
    }
    return 'Pending'
  }
}
