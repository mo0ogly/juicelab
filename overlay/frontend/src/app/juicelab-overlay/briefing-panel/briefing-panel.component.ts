/*
 * juicelab-overlay - Briefing panel
 *
 * Replaces the legacy "before journal" tab. Shows the student WHAT the
 * challenge is about and WHICH concepts to internalize, before they start
 * attacking. The briefing pack is a public asset (no solutions inside) so
 * any agent reviewing it can verify it does not leak the answer.
 *
 * SPDX-License-Identifier: MIT
 */

import { CommonModule } from '@angular/common'
import { Component, computed, inject, input } from '@angular/core'
import { MatCardModule } from '@angular/material/card'
import { MatIconModule } from '@angular/material/icon'
import { toObservable, toSignal } from '@angular/core/rxjs-interop'
import { TranslateModule } from '@ngx-translate/core'
import { catchError, of, switchMap } from 'rxjs'

import { type BriefingPack } from '../models/juicelab.types'
import { JuicelabPackService } from '../services/juicelab-pack.service'
import { JuicelabStateService } from '../services/juicelab-state.service'

@Component({
  selector: 'juicelab-briefing-panel',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, TranslateModule],
  template: `
    <mat-card class="briefing">
      <div class="brief-head">
        <mat-icon class="head-icon">flag</mat-icon>
        <div class="head-text">
          <div class="head-name">{{ challengeName() }}</div>
          <div class="head-meta">
            <span *ngIf="challengeCategory()" class="cat">{{ challengeCategory() }}</span>
            <span *ngIf="challengeDifficulty()" class="diff">{{ challengeDifficulty() }}/6</span>
          </div>
        </div>
      </div>

      <div *ngIf="challengeDescription()" class="brief-desc" [innerHTML]="challengeDescription()"></div>

      <ng-container *ngIf="briefing() as b; else fallback">
        <section class="block mission">
          <h3>
            <mat-icon>track_changes</mat-icon>
            {{ 'JUICELAB_BRIEFING_MISSION' | translate }}
          </h3>
          <div class="mission-body">{{ missionText(b) }}</div>
        </section>

        <section class="block concepts" *ngIf="b.concepts?.length">
          <h3>
            <mat-icon>lightbulb_outline</mat-icon>
            {{ 'JUICELAB_BRIEFING_CONCEPTS' | translate }}
          </h3>
          <div *ngFor="let c of b.concepts" class="concept-card">
            <div class="concept-title">{{ conceptTitle(c) }}</div>
            <div class="concept-body">{{ conceptBody(c) }}</div>
          </div>
        </section>

        <div class="hint-tip">
          <mat-icon>info_outline</mat-icon>
          <span>{{ 'JUICELAB_BRIEFING_HINT_TIP' | translate }}</span>
        </div>
      </ng-container>

      <ng-template #fallback>
        <div *ngIf="loading()" class="loading">
          {{ 'JUICELAB_BRIEFING_LOADING' | translate }}
        </div>
        <div *ngIf="!loading()" class="placeholder">
          {{ 'JUICELAB_BRIEFING_NOTAVAILABLE' | translate }}
        </div>
      </ng-template>
    </mat-card>
  `,
  styles: [`
    .briefing { max-width: 760px; margin: 16px 0; padding: 0; color: inherit; }
    .brief-head {
      display: flex; align-items: flex-start; gap: 12px;
      padding: 14px 18px;
      border-bottom: 1px solid currentColor;
      border-bottom-color: rgba(127,127,127,0.18);
    }
    .head-icon { font-size: 28px; width: 28px; height: 28px; color: #38bdf8; margin-top: 2px; }
    .head-text { flex: 1; }
    .head-name { font-size: 18px; font-weight: 700; line-height: 1.3; }
    .head-meta { display: flex; gap: 8px; margin-top: 4px; font-size: 11px; opacity: 0.75; }
    .head-meta .cat { padding: 1px 6px; border: 1px solid currentColor; border-radius: 4px; }

    .brief-desc {
      padding: 12px 18px;
      font-size: 13px; line-height: 1.55; opacity: 0.85;
      border-bottom: 1px solid rgba(127,127,127,0.12);
    }

    .block { padding: 14px 18px; border-bottom: 1px solid rgba(127,127,127,0.12); }
    .block:last-of-type { border-bottom: 0; }
    .block h3 {
      display: flex; align-items: center; gap: 8px;
      margin: 0 0 10px; font-size: 14px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.6px; opacity: 0.85;
    }
    .block h3 mat-icon { font-size: 18px; width: 18px; height: 18px; color: #38bdf8; }

    .mission-body { font-size: 14px; line-height: 1.6; white-space: pre-line; }

    .concept-card {
      padding: 10px 12px; margin-bottom: 8px;
      background: rgba(56, 189, 248, 0.07);
      border-left: 3px solid #38bdf8;
      border-radius: 4px;
    }
    .concept-card:last-child { margin-bottom: 0; }
    .concept-title { font-weight: 600; font-size: 13px; margin-bottom: 4px; color: #38bdf8; }
    .concept-body { font-size: 13px; line-height: 1.5; opacity: 0.9; white-space: pre-line; }

    .hint-tip {
      display: flex; align-items: center; gap: 8px;
      margin: 10px 18px 14px;
      padding: 10px 12px;
      background: rgba(251, 191, 36, 0.10);
      border: 1px dashed rgba(251, 191, 36, 0.45);
      border-radius: 6px;
      font-size: 12px; line-height: 1.5;
    }
    .hint-tip mat-icon { font-size: 18px; width: 18px; height: 18px; color: #fbbf24; }

    .loading, .placeholder {
      padding: 28px 18px; text-align: center;
      font-size: 13px; opacity: 0.6; font-style: italic;
    }
  `],
})
export class BriefingPanelComponent {
  private readonly packSvc = inject(JuicelabPackService)
  private readonly stateSvc = inject(JuicelabStateService)

  readonly challengeKey = input.required<string>()
  readonly challengeName = input<string>('')
  readonly challengeDescription = input<string>('')
  readonly challengeCategory = input<string>('')
  readonly challengeDifficulty = input<number>(0)

  readonly language = computed(() => this.stateSvc.state().student.language)

  private readonly briefingResult = toSignal(
    toObservable(this.challengeKey).pipe(
      switchMap(k => this.packSvc.getBriefing(k).pipe(
        catchError(() => of(null as BriefingPack | null)),
      )),
    ),
    { initialValue: null as BriefingPack | null },
  )

  readonly briefing = computed(() => this.briefingResult())
  readonly loading = computed(() => false)

  missionText(b: BriefingPack): string {
    return (this.language() === 'fr' ? b.mission_fr : b.mission_en)?.trim() ?? ''
  }

  conceptTitle(c: { title_fr: string, title_en: string }): string {
    return this.language() === 'fr' ? c.title_fr : c.title_en
  }

  conceptBody(c: { body_fr: string, body_en: string }): string {
    return (this.language() === 'fr' ? c.body_fr : c.body_en)?.trim() ?? ''
  }
}
