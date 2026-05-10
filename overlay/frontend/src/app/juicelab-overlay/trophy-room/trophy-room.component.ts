/*
 * juicelab-overlay - Trophy room (hidden route)
 *
 * Standalone Angular component mounted at /#/cabinet (deliberately not
 * linked from any navbar entry). Displays the CTF flags the student has
 * verified through the dashboard /api/verify-flag endpoint as gold
 * trophies. Pure local read : the flag_captured boolean lives in
 * juicelab.state.challenges[key] and is set by journal-form on a
 * successful verify response.
 *
 * Pedagogical intent : students who explore the URL space (or read the
 * source) discover this gamified achievements page. There is no link, no
 * hint, no dropdown — finding it IS the reward.
 *
 * SPDX-License-Identifier: MIT
 */

import { CommonModule } from '@angular/common'
import { Component, computed, inject, signal } from '@angular/core'
import { MatButtonModule } from '@angular/material/button'
import { MatCardModule } from '@angular/material/card'
import { MatIconModule } from '@angular/material/icon'
import { RouterModule } from '@angular/router'
import { toSignal } from '@angular/core/rxjs-interop'
import { TranslateModule } from '@ngx-translate/core'

import { type SelectedChallenge } from '../models/juicelab.types'
import { JuicelabPackService } from '../services/juicelab-pack.service'
import { JuicelabStateService } from '../services/juicelab-state.service'

interface TrophyRow {
  key: string
  name: string
  difficulty: number
  category: string
  capturedAt: string | null
}

@Component({
  selector: 'juicelab-trophy-room',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    TranslateModule,
  ],
  template: `
    <div class="cabinet-root">
      <header class="header">
        <mat-icon class="crown">military_tech</mat-icon>
        <div class="header-text">
          <h1>{{ 'JUICELAB_TROPHY_TITLE' | translate }}</h1>
          <p class="lead">{{ 'JUICELAB_TROPHY_LEAD' | translate }}</p>
        </div>
        <a mat-stroked-button color="primary" routerLink="/juicelab" class="back">
          <mat-icon>arrow_back</mat-icon>
          {{ 'JUICELAB_TROPHY_BACK' | translate }}
        </a>
      </header>

      <div class="counter">
        {{ 'JUICELAB_TROPHY_COUNTER' | translate:{ captured: captured(), total: total() } }}
      </div>

      <ng-container *ngIf="captured() > 0 || legendUnlocked(); else emptyState">
        <div class="grid">
          <article *ngFor="let t of capturedRows()" class="trophy">
            <div class="trophy-icon">
              <mat-icon>emoji_events</mat-icon>
            </div>
            <div class="trophy-name">{{ t.name }}</div>
            <div class="trophy-meta">
              <span class="cat">{{ t.category }}</span>
              <span class="diff">{{ t.difficulty }}/6</span>
            </div>
            <div *ngIf="t.capturedAt" class="trophy-ts">
              {{ 'JUICELAB_TROPHY_CAPTURED_AT' | translate }}
              {{ formatTimestamp(t.capturedAt) }}
            </div>
          </article>
          <article *ngIf="legendUnlocked()" class="trophy trophy-legend">
            <div class="trophy-icon">
              <mat-icon>auto_awesome</mat-icon>
            </div>
            <div class="trophy-name">{{ 'JUICELAB_TROPHY_LEGEND_NAME' | translate }}</div>
            <div class="trophy-meta">
              <span class="cat">F12</span>
            </div>
            <div class="trophy-ts">{{ 'JUICELAB_TROPHY_LEGEND_SUCCESS' | translate }}</div>
          </article>
        </div>
      </ng-container>

      <ng-template #emptyState>
        <div class="empty">
          <mat-icon>shield</mat-icon>
          <h2>{{ 'JUICELAB_TROPHY_EMPTY_TITLE' | translate }}</h2>
          <p>{{ 'JUICELAB_TROPHY_EMPTY_BODY' | translate }}</p>
        </div>
      </ng-template>

      <div
        class="legend-hint"
        data-rot13="ivtvynapr"
        data-layer-1="inspect this element via F12"
        data-layer-2="decode the data-rot13 attribute (Caesar +13)"
        data-layer-3="unhide the form below (display:none) and submit the decoded word"
        aria-hidden="true"
        style="display: none"
      ></div>
      <form class="legend-form" style="display: none" (submit)="$event.preventDefault(); checkLegend(legendField.value)">
        <input #legendField type="text" autocomplete="off"
          [placeholder]="'JUICELAB_TROPHY_LEGEND_PLACEHOLDER' | translate" />
        <button type="submit" mat-stroked-button color="primary">
          {{ 'JUICELAB_TROPHY_LEGEND_VALIDATE' | translate }}
        </button>
        <div *ngIf="legendError()" class="legend-error">
          {{ 'JUICELAB_TROPHY_LEGEND_FAIL' | translate }}
        </div>
      </form>
    </div>
  `,
  styles: [`
    .cabinet-root {
      max-width: 1100px; margin: 32px auto; padding: 24px;
      color: inherit;
      background: radial-gradient(ellipse at top, rgba(251, 191, 36, 0.10) 0%, transparent 70%);
      border-radius: 16px;
    }
    .header {
      display: flex; align-items: center; gap: 18px;
      padding-bottom: 20px;
      border-bottom: 1px solid rgba(127,127,127,0.18);
    }
    .crown { font-size: 48px; width: 48px; height: 48px; color: #fbbf24; }
    .header-text { flex: 1; }
    h1 { margin: 0 0 4px; font-size: 26px; font-weight: 800; }
    .lead { margin: 0; opacity: 0.72; font-size: 14px; line-height: 1.5; }
    .back { white-space: nowrap; }

    .counter {
      margin: 16px 0 24px;
      font-size: 14px; opacity: 0.65;
      text-transform: uppercase; letter-spacing: 1px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 16px;
    }

    .trophy {
      display: flex; flex-direction: column; align-items: center;
      padding: 20px 16px;
      background: linear-gradient(180deg, rgba(251, 191, 36, 0.18), rgba(251, 191, 36, 0.04));
      border: 1px solid rgba(251, 191, 36, 0.55);
      border-radius: 12px;
      text-align: center;
      box-shadow: 0 4px 16px rgba(251, 191, 36, 0.12);
      transition: transform 0.18s ease;
    }
    .trophy:hover {
      transform: translateY(-3px);
      box-shadow: 0 8px 24px rgba(251, 191, 36, 0.22);
    }
    .trophy-icon mat-icon {
      font-size: 56px; width: 56px; height: 56px; color: #fbbf24;
      filter: drop-shadow(0 2px 8px rgba(251, 191, 36, 0.6));
    }
    .trophy-name {
      margin-top: 10px;
      font-size: 15px; font-weight: 700; line-height: 1.25;
    }
    .trophy-meta {
      display: flex; gap: 8px; margin-top: 8px;
      font-size: 11px; opacity: 0.72;
    }
    .trophy-meta .cat { padding: 1px 6px; border: 1px solid currentColor; border-radius: 4px; }
    .trophy-ts {
      margin-top: 10px;
      font-size: 11px; opacity: 0.55;
      font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
    }

    .empty {
      display: flex; flex-direction: column; align-items: center;
      padding: 56px 24px; text-align: center;
      opacity: 0.7;
    }
    .empty mat-icon { font-size: 64px; width: 64px; height: 64px; color: #94a3b8; }
    .empty h2 { margin: 14px 0 6px; font-size: 18px; }
    .empty p { margin: 0; max-width: 480px; line-height: 1.5; font-size: 13px; }

    .trophy-legend {
      background: linear-gradient(180deg, rgba(168, 85, 247, 0.22), rgba(168, 85, 247, 0.06));
      border-color: rgba(168, 85, 247, 0.7);
      box-shadow: 0 4px 20px rgba(168, 85, 247, 0.25);
    }
    .trophy-legend .trophy-icon mat-icon {
      color: #c084fc;
      filter: drop-shadow(0 2px 10px rgba(192, 132, 252, 0.7));
    }

    .legend-form { margin-top: 24px; padding: 12px; gap: 8px; align-items: center; }
    .legend-form input {
      padding: 6px 10px; border-radius: 6px;
      border: 1px solid rgba(127, 127, 127, 0.4);
      background: transparent; color: inherit;
      font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
    }
    .legend-error { color: #f87171; font-size: 12px; margin-left: 8px; }
  `],
})
export class TrophyRoomComponent {
  private static readonly LEGEND_KEYWORD_ROT13 = 'ivtvynapr'
  private static readonly LEGEND_STORAGE_KEY = 'juicelab_legend_unlocked'

  private readonly stateSvc = inject(JuicelabStateService)
  private readonly packSvc = inject(JuicelabPackService)

  private readonly challenges = toSignal(
    this.packSvc.getSelectedChallenges(),
    { initialValue: [] as SelectedChallenge[] },
  )

  readonly legendUnlocked = signal<boolean>(this.readLegendStorage())
  readonly legendError = signal<boolean>(false)

  private readLegendStorage(): boolean {
    try {
      return window.localStorage.getItem(TrophyRoomComponent.LEGEND_STORAGE_KEY) === 'true'
    } catch {
      return false
    }
  }

  checkLegend(raw: string | null | undefined): void {
    const guess = (raw ?? '').trim().toLowerCase()
    const expected = TrophyRoomComponent.rot13(TrophyRoomComponent.LEGEND_KEYWORD_ROT13)
    if (guess === expected) {
      this.legendUnlocked.set(true)
      this.legendError.set(false)
      try {
        window.localStorage.setItem(TrophyRoomComponent.LEGEND_STORAGE_KEY, 'true')
      } catch {
        // localStorage unavailable (private mode etc.) — keep in-memory only
      }
    } else {
      this.legendError.set(true)
    }
  }

  private static rot13(s: string): string {
    return s.replace(/[a-z]/gi, (c) => {
      const code = c.charCodeAt(0)
      const base = code >= 97 ? 97 : 65
      return String.fromCharCode(((code - base + 13) % 26) + base)
    })
  }

  readonly capturedRows = computed<TrophyRow[]>(() => {
    const list = this.challenges()
    const stateMap = this.stateSvc.state().challenges
    return list
      .map<TrophyRow | null>((c) => {
        const slot = stateMap[c.key]
        if (!slot?.flag_captured) return null
        return {
          key: c.key,
          name: c.name_official,
          difficulty: c.difficulty,
          category: c.category,
          capturedAt: slot.flag_captured_at,
        }
      })
      .filter((row): row is TrophyRow => row !== null)
  })

  readonly captured = computed(() => this.capturedRows().length)
  readonly total = computed(() => this.challenges().length)

  formatTimestamp(iso: string): string {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    const dd = String(d.getDate()).padStart(2, '0')
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const hh = String(d.getHours()).padStart(2, '0')
    const mn = String(d.getMinutes()).padStart(2, '0')
    return dd + '/' + mm + ' ' + hh + ':' + mn
  }
}
