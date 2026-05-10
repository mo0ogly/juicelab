/*
 * juicelab-overlay - Hints panel component
 *
 * Phase B: each hint level is fetched on demand via /api/juicelab/hint.
 * The server enforces progression and refuses N+1 if N has not been
 * consumed by the same student token. The component never holds the
 * full pack; it accumulates revealed hints in a signal-backed map.
 *
 * SPDX-License-Identifier: MIT
 */

import { CommonModule } from '@angular/common'
import { Component, computed, effect, inject, input, signal } from '@angular/core'
import { MatButtonModule } from '@angular/material/button'
import { MatCardModule } from '@angular/material/card'
import { MatIconModule } from '@angular/material/icon'
import { TranslateModule, TranslateService } from '@ngx-translate/core'

import { type HintLevel, type HintResponse } from '../models/juicelab.types'
import { JuicelabAuthService } from '../services/juicelab-auth.service'
import { JuicelabPackService } from '../services/juicelab-pack.service'
import { JuicelabScoringService } from '../services/juicelab-scoring.service'
import { JuicelabStateService } from '../services/juicelab-state.service'
import { JuicelabSyncService } from '../services/juicelab-sync.service'

const ORDER: HintLevel[] = ['N1', 'N2', 'N3', 'N4', 'N5']

@Component({
  selector: 'juicelab-hints-panel',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatButtonModule, MatIconModule, TranslateModule],
  template: `
    <mat-card class="hints-panel">
      <mat-card-title>
        <mat-icon>lightbulb</mat-icon>
        {{ 'JUICELAB_HINTS_TITLE' | translate }}
      </mat-card-title>
      <mat-card-subtitle>
        {{ 'JUICELAB_HINTS_SCORE_CURRENT' | translate }} : <strong>{{ score() }}</strong>
        | {{ 'JUICELAB_HINTS_CONSUMED' | translate }} : <strong>{{ consumed().length }}</strong> / 5
      </mat-card-subtitle>
      <mat-card-content>
        <div *ngFor="let lvl of order" class="hint-row" [class.consumed]="isConsumed(lvl)">
          <div class="hint-header">
            <strong>{{ lvl }}</strong>
            <span class="cost">{{ 'JUICELAB_HINTS_COST' | translate }} {{ costFor(lvl) }}%</span>
            <button
              *ngIf="!isConsumed(lvl)"
              mat-stroked-button
              color="primary"
              (click)="reveal(lvl)"
              [disabled]="!canReveal(lvl) || loading()"
            >
              {{ (loading() ? 'JUICELAB_HINTS_LOADING' : 'JUICELAB_HINTS_REVEAL') | translate }}
            </button>
          </div>
          <div *ngIf="isConsumed(lvl) && revealedText(lvl)" class="hint-body">
            {{ revealedText(lvl) }}
          </div>
        </div>
        <div *ngIf="error() as err" class="error">{{ err }}</div>
      </mat-card-content>
    </mat-card>
  `,
  styles: [`
    .hints-panel { max-width: 720px; margin: 16px 0; color: inherit; }
    .hint-row { padding: 8px 0; border-bottom: 1px solid currentColor; border-bottom-color: rgba(127,127,127,0.25); }
    .hint-row.consumed { background: rgba(255, 235, 130, 0.18); }
    .hint-header { display: flex; gap: 12px; align-items: center; }
    .cost { opacity: 0.65; font-size: 12px; flex: 1; }
    .hint-body { padding: 8px 0 0 28px; line-height: 1.5; }
    .error { color: #f87171; padding: 8px; font-size: 13px; }
  `],
})
export class HintsPanelComponent {
  private readonly packSvc = inject(JuicelabPackService)
  private readonly stateSvc = inject(JuicelabStateService)
  private readonly scoringSvc = inject(JuicelabScoringService)
  private readonly syncSvc = inject(JuicelabSyncService)
  private readonly authSvc = inject(JuicelabAuthService)
  private readonly translate = inject(TranslateService)

  readonly challengeKey = input.required<string>()

  readonly order = ORDER
  readonly revealed = signal<Map<HintLevel, HintResponse>>(new Map())
  readonly loading = signal(false)
  readonly error = signal<string | null>(null)

  readonly state = computed(() => this.stateSvc.state().challenges[this.challengeKey()])
  readonly consumed = computed(() => this.state()?.hints_consumed ?? [])
  readonly score = computed(() => this.scoringSvc.scoreFromConsumedHints(this.consumed()))
  readonly language = computed(() => this.stateSvc.state().student.language)

  constructor () {
    // Hydrate the in-memory revealed map from the server for hints already
    // consumed in a previous session. Without this, after a reload the user
    // sees N1 marked as consumed but with no text body.
    //
    // The fetch must be SEQUENTIAL in N1 -> N2 -> N3 order : the server
    // tracks consumed levels in an in-memory map and refuses level N+1 if
    // level N is missing from its set. If we fired the requests in
    // parallel, the network could deliver N3 before N1 and the server
    // would 403. Sequential warm-up also re-populates the server map after
    // a Juice Shop restart that wiped it.
    effect(() => {
      const consumed = this.consumed()
      const key = this.challengeKey()
      if (!key || consumed.length === 0) return

      const cur = this.revealed()
      const ordered = ORDER.filter(lvl => consumed.includes(lvl) && !cur.has(lvl))
      if (ordered.length === 0) return

      this.warmUpHints(key, ordered, 0)
    })
  }

  private warmUpHints (key: string, levels: HintLevel[], index: number): void {
    if (index >= levels.length) return
    const lvl = levels[index]
    this.packSvc.getHint(key, lvl).subscribe({
      next: (hint) => {
        const next = new Map(this.revealed())
        next.set(lvl, hint)
        this.revealed.set(next)
        this.warmUpHints(key, levels, index + 1)
      },
      error: () => {
        // Stop the chain on first failure — pushing further requests would
        // also fail because the server gating depends on the previous
        // level being acknowledged.
      },
    })
  }

  costFor(lvl: HintLevel): number {
    return this.revealed().get(lvl)?.cost_pct ?? this.scoringSvc.costOf(lvl)
  }

  revealedText(lvl: HintLevel): string {
    const entry = this.revealed().get(lvl)
    if (!entry) return ''
    return this.language() === 'fr' ? entry.text_fr : entry.text_en
  }

  isConsumed(lvl: HintLevel): boolean {
    return this.consumed().includes(lvl)
  }

  canReveal(lvl: HintLevel): boolean {
    const idx = ORDER.indexOf(lvl)
    if (idx === 0) return true
    return this.isConsumed(ORDER[idx - 1])
  }

  reveal(lvl: HintLevel): void {
    if (this.loading()) return
    this.error.set(null)
    this.loading.set(true)
    this.packSvc.getHint(this.challengeKey(), lvl).subscribe({
      next: (hint) => {
        this.loading.set(false)
        const next = new Map(this.revealed())
        next.set(lvl, hint)
        this.revealed.set(next)

        this.stateSvc.getOrInitChallenge(this.challengeKey())
        const consumedNext = [...this.consumed(), lvl]
        const newScore = this.scoringSvc.scoreFromConsumedHints(consumedNext)
        this.stateSvc.consumeHint(this.challengeKey(), lvl, newScore)

        const s = this.stateSvc.state()
        this.syncSvc.send({
          student_token: s.student.token,
          cohort_id: s.student.cohort,
          event_type: 'hint_revealed',
          challenge_key: this.challengeKey(),
          data: { level: lvl, score_after: newScore, cost_pct: hint.cost_pct },
          client_timestamp: new Date().toISOString(),
        })
      },
      error: (err) => {
        this.loading.set(false)
        // Ne PAS rethrow : si on laisse l'erreur remonter, Juice Shop core
        // affiche "An unexpected error occurred undefined" via son
        // gestionnaire global. On la consomme ici proprement.
        if (err?.status === 401) {
          this.authSvc.markUnauthenticated()
          this.error.set(this.translate.instant('JUICELAB_HINTS_ERR_AUTH'))
        } else if (err?.status === 403) {
          const required = err?.error?.required ?? '?'
          this.error.set(this.translate.instant('JUICELAB_HINTS_ERR_GATING', { required, level: lvl }))
        } else if (err?.status === 404) {
          this.error.set(this.translate.instant('JUICELAB_HINTS_ERR_NOTFOUND', { key: this.challengeKey() }))
        } else {
          this.error.set(this.translate.instant('JUICELAB_HINTS_ERR_NETWORK', { status: err?.status ?? '?' }))
        }
      },
    })
  }
}
